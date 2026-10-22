import json

import pytest

from gateway.domain.chat import (
    ChatRequest,
    GenerationOptions,
    ImagePart,
    Message,
    NamedToolChoice,
    TextPart,
    ToolCall,
    ToolDefinition,
    WebSearch,
)
from gateway.domain.errors import InvalidRequestError, NotFoundError, PayloadTooLargeError
from gateway.domain.media import ImageGenerationRequest, SpeechRequest
from gateway.domain.models import Backend
from gateway.domain.services.crawl_notices import (
    CRAWL_PREFIX,
    CrawlNoticeFilter,
    strip_crawl_notices,
)
from gateway.domain.services.data_uri import decode_data_uri
from gateway.domain.services.image_sizing import generation_prompt_object, size_style
from gateway.domain.services.routing import (
    ModelAlias,
    ModelDirectorySnapshot,
    choose_route,
    short_name_index,
)
from gateway.domain.services.sampling import OutputCap, SamplingPolicy
from gateway.domain.services.speech import speech_prompt_object
from gateway.domain.services.tokens import estimate_tokens
from gateway.domain.services.tool_protocol import (
    format_tool_call,
    parse_tool_calls,
    render_tool_instructions,
)
from gateway.domain.services.transcript import CONTINUE_INSTRUCTION, render_prompt

WEATHER = ToolDefinition(
    name="get_weather",
    description="Current weather",
    parameters={"type": "object", "properties": {"city": {"type": "string"}}},
)


def user(text: str) -> Message:
    return Message(role="user", content=(TextPart(text),))


# --- tool protocol -----------------------------------------------------------------------


class TestToolProtocol:
    def test_instructions_absent_without_tools_or_with_none(self) -> None:
        assert render_tool_instructions([], "auto") is None
        assert render_tool_instructions([WEATHER], "none") is None

    def test_instructions_describe_tools_and_choice(self) -> None:
        text = render_tool_instructions([WEATHER], NamedToolChoice("get_weather"))
        assert text is not None
        assert "- get_weather: Current weather" in text
        assert '"city"' in text
        assert 'MUST call the tool "get_weather"' in text
        assert "at least one tool" in (render_tool_instructions([WEATHER], "required") or "")

    def test_parses_calls_and_keeps_surrounding_text(self) -> None:
        reply = 'Checking.\n<tool_call>{"name": "get_weather", "arguments": {"city": "Paris", "nested": {"a": [1, 2]}}}</tool_call>'
        parsed = parse_tool_calls(reply, [WEATHER], id_factory=lambda: "call_1")
        assert parsed.text == "Checking."
        assert parsed.tool_calls == (
            ToolCall(
                "call_1", "get_weather", json.dumps({"city": "Paris", "nested": {"a": [1, 2]}})
            ),
        )

    def test_accepts_fences_parameters_key_and_string_arguments(self) -> None:
        reply = (
            '```json\n<tool_call>{"name": "get_weather", "parameters": {"city": "Lyon"}}</tool_call>\n```\n'
            '<tool_call>{"name": "get_weather", "arguments": "{\\"city\\": \\"Nice\\"}"}</tool_call>'
        )
        parsed = parse_tool_calls(reply, [WEATHER])
        assert parsed.text is None
        assert [json.loads(call.arguments)["city"] for call in parsed.tool_calls] == [
            "Lyon",
            "Nice",
        ]

    def test_invented_results_after_the_call_are_dropped(self) -> None:
        # Observed with a real model: it calls the tool, then invents the result and answers.
        reply = (
            'Let me check.\n<tool_call>{"name": "get_weather", "arguments": {"city": "Lyon"}}</tool_call>\n'
            "<tool_result>\nTemperature: 12C\n</tool_result>\n\nThe weather in Lyon is 12C."
        )
        parsed = parse_tool_calls(reply, [WEATHER])
        assert parsed.text == "Let me check."
        assert [call.name for call in parsed.tool_calls] == ["get_weather"]

    def test_instructions_tell_the_model_to_stop_after_calls(self) -> None:
        assert "STOP" in (render_tool_instructions([WEATHER], "auto") or "")

    def test_undeclared_or_invalid_blocks_stay_text(self) -> None:
        reply = '<tool_call>{"name": "rm_rf"}</tool_call> and <tool_call>{broken</tool_call>'
        parsed = parse_tool_calls(reply, [WEATHER])
        assert parsed.tool_calls == ()
        assert parsed.text == reply

    def test_unterminated_block_is_linear_and_harmless(self) -> None:
        reply = "<tool_call>{" * 20_000
        parsed = parse_tool_calls(reply, [WEATHER])
        assert parsed.tool_calls == ()

    def test_format_tool_call_round_trips(self) -> None:
        call = ToolCall("call_9", "get_weather", '{"city": "Rome"}')
        parsed = parse_tool_calls(format_tool_call(call), [WEATHER], id_factory=lambda: "call_9")
        assert parsed.tool_calls == (call,)


# --- transcript ----------------------------------------------------------------------------


class TestTranscript:
    def test_single_user_message_is_sent_verbatim(self) -> None:
        assert render_prompt([user("  Hello\n\nworld  ")]) == "  Hello\n\nworld  "

    def test_system_prompt_becomes_instructions(self) -> None:
        prompt = render_prompt(
            [Message(role="system", content=(TextPart("Be brief."),)), user("Hi")]
        )
        assert prompt == "<instructions>\nBe brief.\n</instructions>\n\nHi"

    def test_multi_turn_with_tools_and_images(self) -> None:
        image = ImagePart("https://example.com/cat.png")
        messages = [
            Message(role="user", content=(TextPart("Weather and photo?"), image)),
            Message(
                role="assistant",
                tool_calls=(ToolCall("call_1", "get_weather", '{"city":"Paris"}'),),
            ),
            Message(role="tool", content=(TextPart("12C"),), tool_call_id="call_1"),
        ]
        prompt = render_prompt(messages, tool_instructions="# Tools", image_labels={image: 1})
        assert prompt.startswith("<instructions>\n# Tools\n</instructions>")
        assert "<user>\nWeather and photo?\n[image 1]\n</user>" in prompt
        assert (
            '<tool_call>{"name": "get_weather", "arguments": {"city": "Paris"}}</tool_call>'
            in prompt
        )
        assert '<tool_result name="get_weather" id="call_1">\n12C\n</tool_result>' in prompt
        assert prompt.endswith(CONTINUE_INSTRUCTION)


# --- routing -------------------------------------------------------------------------------


DIRECTORY = ModelDirectorySnapshot(
    native=frozenset({"gpt-5", "gpt-4o-mini"}),
    legacy=frozenset({"claude-sonnet-4-5-20250929", "gpt-4o-mini", "sonar"}),
    aliases=(ModelAlias("my-model", "gpt-5"), ModelAlias("claude-*", "claude-sonnet-4-5-20250929")),
    legacy_known=True,
    text_only=frozenset({"sonar"}),
)


class TestRouting:
    def test_native_model(self) -> None:
        route = choose_route(ChatRequest("gpt-5", (user("hi"),)), DIRECTORY)
        assert (route.backend, route.model) == (Backend.NATIVE, "gpt-5")

    def test_alias_exact_and_pattern(self) -> None:
        assert choose_route(ChatRequest("my-model", (user("hi"),)), DIRECTORY).model == "gpt-5"
        route = choose_route(ChatRequest("claude-opus-9", (user("hi"),)), DIRECTORY)
        assert (route.backend, route.model) == (Backend.LEGACY, "claude-sonnet-4-5-20250929")

    def test_images_files_and_web_search_force_legacy(self) -> None:
        vision = ChatRequest(
            "gpt-4o-mini", (Message(role="user", content=(ImagePart("https://x/y.png"),)),)
        )
        assert choose_route(vision, DIRECTORY).backend is Backend.LEGACY
        web = ChatRequest("gpt-4o-mini", (user("news"),), web_search=WebSearch())
        assert choose_route(web, DIRECTORY).web_search
        suffix = choose_route(ChatRequest("gpt-4o-mini:online", (user("news"),)), DIRECTORY)
        assert (suffix.backend, suffix.model, suffix.web_search) == (
            Backend.LEGACY,
            "gpt-4o-mini",
            True,
        )
        files = ChatRequest("claude-sonnet-4-5-20250929", (user("doc"),), file_ids=("file-1",))
        assert choose_route(files, DIRECTORY).backend is Backend.LEGACY

    def test_unknown_model(self) -> None:
        with pytest.raises(NotFoundError) as error:
            choose_route(ChatRequest("nope", (user("hi"),)), DIRECTORY)
        assert error.value.code == "model_not_found"
        unknown_catalog = ModelDirectorySnapshot(frozenset(), frozenset(), native_known=False)
        assert (
            choose_route(ChatRequest("nope", (user("hi"),)), unknown_catalog).backend
            is Backend.NATIVE
        )
        # Native list known, legacy catalog unavailable: let the Chat with AI API decide.
        no_legacy = ModelDirectorySnapshot(frozenset({"gpt-5"}), frozenset(), legacy_known=False)
        assert choose_route(ChatRequest("nope", (user("hi"),)), no_legacy).backend is Backend.LEGACY

    def test_vision_requires_an_image_capable_legacy_model(self) -> None:
        image = Message(role="user", content=(TextPart("what?"), ImagePart("https://x/y.png")))
        with pytest.raises(InvalidRequestError) as error:
            choose_route(ChatRequest("sonar", (image,)), DIRECTORY)
        assert error.value.code == "model_not_vision_capable"
        with pytest.raises(NotFoundError):
            choose_route(ChatRequest("gpt-5", (image,)), DIRECTORY)  # native only
        assert (
            choose_route(ChatRequest("gpt-4o-mini", (image,)), DIRECTORY).backend is Backend.LEGACY
        )

    def test_short_names_of_provider_qualified_ids(self) -> None:
        ids = frozenset(
            {
                "us.anthropic.claude-haiku-4-5-20251001-v1:0",
                "us.anthropic.claude-sonnet-4-6",
                "anthropic.claude-opus-4-6-v1",
                "gpt-5",
            }
        )
        index = short_name_index(ids)
        assert index == {
            "claude-haiku-4-5-20251001": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
            "claude-sonnet-4-6": "us.anthropic.claude-sonnet-4-6",
            "claude-opus-4-6": "anthropic.claude-opus-4-6-v1",
        }
        snapshot = ModelDirectorySnapshot(
            native=frozenset({"gpt-5"}),
            legacy=ids - {"gpt-5"},
            legacy_known=True,
            short_names=index,
        )
        route = choose_route(ChatRequest("claude-haiku-4-5-20251001", (user("hi"),)), snapshot)
        assert (route.backend, route.model) == (
            Backend.LEGACY,
            "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        )

    def test_empty_model(self) -> None:
        with pytest.raises(InvalidRequestError):
            choose_route(ChatRequest(" ", (user("hi"),)), DIRECTORY)


# --- sampling policy -------------------------------------------------------------------------


class TestSamplingPolicy:
    options = GenerationOptions(max_output_tokens=50_000, temperature=0.2, top_p=0.9, stop=("x",))

    def test_reasoning_models_drop_sampling_and_cap_output(self) -> None:
        adjusted = SamplingPolicy().apply("gpt-5", self.options)
        assert (adjusted.temperature, adjusted.top_p, adjusted.stop) == (None, None, ())
        assert adjusted.max_output_tokens == 32768

    def test_provider_prefix_and_custom_caps(self) -> None:
        policy = SamplingPolicy(output_caps=(OutputCap("gpt-4o*", 16384),))
        adjusted = policy.apply("openai/gpt-4o-mini", self.options)
        assert adjusted.temperature == 0.2
        assert adjusted.max_output_tokens == 16384
        assert policy.apply("deepseek-chat", self.options).temperature is None

    def test_disabled_dropping_keeps_parameters(self) -> None:
        adjusted = SamplingPolicy(drop_restricted=False).apply("gpt-5", self.options)
        assert adjusted.temperature == 0.2


# --- images and speech -----------------------------------------------------------------------


class TestImageSizing:
    def test_styles(self) -> None:
        assert size_style("gpt-image-1") == "size"
        assert size_style("black-forest-labs/flux-schnell") == "aspect_ratio"
        assert size_style("magic-art_7_0") == "aspect_wh"
        assert size_style("unknown-model") == "none"

    def test_gpt_image_fields(self) -> None:
        prompt_object = generation_prompt_object(
            ImageGenerationRequest(
                prompt="cat",
                model="gpt-image-1",
                n=2,
                size="1536x1024",
                quality="hd",
                style="natural",
            )
        )
        assert prompt_object == {
            "prompt": "cat",
            "size": "1536x1024",
            "n": 2,
            "quality": "high",
            "style": "natural",
        }

    def test_gpt_image_2_required_defaults(self) -> None:
        prompt_object = generation_prompt_object(
            ImageGenerationRequest(prompt="cat", model="gpt-image-2")
        )
        assert prompt_object == {"prompt": "cat", "size": "1024x1024", "quality": "medium"}

    def test_flux_and_magic_art_ratios_and_extra_override(self) -> None:
        flux = generation_prompt_object(
            ImageGenerationRequest(
                prompt="x",
                model="black-forest-labs/flux-schnell",
                size="1792x1024",
                n=3,
                quality="high",
            )
        )
        assert flux == {"prompt": "x", "aspect_ratio": "16:9"}
        magic = generation_prompt_object(
            ImageGenerationRequest(
                prompt="x", model="magic-art_7_0", size="1024x1536", extra={"mode": "relax"}
            )
        )
        assert magic == {"prompt": "x", "aspect_width": 2, "aspect_height": 3, "mode": "relax"}

    def test_invalid_size(self) -> None:
        with pytest.raises(InvalidRequestError):
            generation_prompt_object(
                ImageGenerationRequest(prompt="x", model="gpt-image-1", size="big")
            )
        with pytest.raises(InvalidRequestError):
            generation_prompt_object(
                ImageGenerationRequest(prompt="x", model="black-forest-labs/flux-dev", size="huge")
            )

    def test_speech_fields_per_provider(self) -> None:
        openai = speech_prompt_object(
            SpeechRequest(text="hi", model="tts-1", voice="nova", speed=1.5)
        )
        assert openai == {"text": "hi", "voice": "nova", "response_format": "mp3", "speed": 1.5}
        eleven = speech_prompt_object(
            SpeechRequest(text="hi", model="elevenlabs-tts", voice="abc123")
        )
        assert eleven == {"text": "hi", "voice_id": "abc123"}


# --- small helpers -----------------------------------------------------------------------------


class TestCrawlNotices:
    def test_removes_notice_lines_across_chunk_boundaries(self) -> None:
        notice_filter = CrawlNoticeFilter()
        chunks = [
            "Intro\n\U0001f310 Crawl",
            "ing site https://a.b/c\nAnswer ",
            "\U0001f310 globe stays\n",
        ]
        output = "".join(notice_filter.feed(chunk) for chunk in chunks) + notice_filter.flush()
        assert output == "Intro\nAnswer \U0001f310 globe stays\n"

    def test_keeps_lines_that_merely_start_with_the_globe(self) -> None:
        assert strip_crawl_notices("\U0001f310 World news\nok") == "\U0001f310 World news\nok"
        assert strip_crawl_notices(f"{CRAWL_PREFIX} https://x\n") == ""


class TestDataUri:
    def test_decodes_base64(self) -> None:
        decoded = decode_data_uri("data:image/png;base64,iVBORw0K", max_bytes=1024)
        assert decoded.media_type == "image/png"
        assert decoded.extension == "png"
        assert decoded.content.startswith(b"\x89PNG")

    def test_rejects_invalid_and_oversized(self) -> None:
        with pytest.raises(InvalidRequestError):
            decode_data_uri("data:image/png,raw", max_bytes=1024)
        with pytest.raises(PayloadTooLargeError):
            decode_data_uri("data:image/png;base64," + "A" * 4000, max_bytes=1024)


def test_token_estimate() -> None:
    assert estimate_tokens(None) == 0
    assert estimate_tokens("abcd" * 10) == 10
