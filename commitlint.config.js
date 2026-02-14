
// ============================================================
// Commitlint Configuration - Gitmoji Compatible
// ============================================================
// Ce fichier valide les messages de commit selon la convention gitmoji
// Compatible avec semantic-release-gitmoji
//
// Format accepté:
// ✨ feat(Core): Add new feature
// 🐛 fix(Gateway): Fix authentication bug
// 💥 feat!: Breaking change
// ============================================================

module.exports = {
  // Extend gitmoji configuration
  extends: ['gitmoji'],

  // Parser options pour gérer les gitmojis
  parserPreset: {
    parserOpts: {
      headerPattern: /^(?::([\w-]+):|\uD83C[\uDF00-\uDFFF]|\uD83D[\uDC00-\uDE4F\uDE80-\uDEFF]|[\u2600-\u2B55])\s(\w+)(?:\(([^\)]+)\))?!?:\s(.+)$/,
      headerCorrespondence: ['emoji', 'type', 'scope', 'subject']
    }
  },

  // Règles personnalisées
  rules: {
    // Autoriser les gitmojis au début
    'header-max-length': [2, 'always', 100],
    'type-empty': [0], // Désactivé car le type peut être remplacé par l'emoji
    'subject-empty': [2, 'never'],
    'subject-case': [
      2,
      'never',
      ['sentence-case', 'start-case', 'pascal-case', 'upper-case']
    ],

    // Scopes autorisés - Tous en PascalCase (Standard Enterprise)
    'scope-enum': [
      2,
      'always',
      [
        'Core',       // Logique métier principale
        'Gateway',    // API Gateway
        'Docker',     // Containerisation
        'Config',     // Configuration
        'Logging',    // Système de logs
        'Cicd',       // CI/CD pipelines
        'Deps',       // Dépendances (Dependabot)
        'DepsDev',    // Dépendances dev (Dependabot)
        'Release'     // Releases automatiques
      ]
    ],
    'scope-case': [2, 'always', 'pascal-case'],

    // Types autorisés (conventionalcommits)
    'type-enum': [
      2,
      'always',
      [
        'feat',     // ✨ Nouvelle fonctionnalité
        'fix',      // 🐛 Correction de bug
        'docs',     // 📝 Documentation
        'style',    // 🎨 Formatage, style
        'refactor', // ♻️ Refactoring
        'perf',     // ⚡ Performance
        'test',     // ✅ Tests
        'build',    // 📦 Build system
        'ci',       // 🔄 CI/CD
        'chore',    // 🔧 Maintenance
        'revert'    // ⏪ Revert
      ]
    ],
    'type-case': [2, 'always', 'lower-case'],
  },

  // Ignorer certains patterns (commits automatiques)
  ignores: [
    (message) => message.includes('[skip ci]'),
    (message) => message.includes('chore(release)'),
    (message) => message.includes('chore(Release)'),
    (message) => message.startsWith('Merge'),
    (message) => message.startsWith('Initial commit')
  ],

  // Configuration du prompt (si tu utilises commitizen)
  prompt: {
    questions: {
      type: {
        description: "Select the type of change that you're committing",
        enum: {
          feat: {
            description: '✨ A new feature',
            title: 'Features',
            emoji: '✨'
          },
          fix: {
            description: '🐛 A bug fix',
            title: 'Bug Fixes',
            emoji: '🐛'
          },
          docs: {
            description: '📝 Documentation only changes',
            title: 'Documentation',
            emoji: '📝'
          },
          style: {
            description: '🎨 Code style changes (formatting, etc)',
            title: 'Styles',
            emoji: '🎨'
          },
          refactor: {
            description: '♻️ Code refactoring',
            title: 'Code Refactoring',
            emoji: '♻️'
          },
          perf: {
            description: '⚡ Performance improvements',
            title: 'Performance',
            emoji: '⚡'
          },
          test: {
            description: '✅ Adding or updating tests',
            title: 'Tests',
            emoji: '✅'
          },
          build: {
            description: '📦 Build system or dependencies',
            title: 'Builds',
            emoji: '📦'
          },
          ci: {
            description: '🔄 CI/CD configuration',
            title: 'CI/CD',
            emoji: '🔄'
          },
          chore: {
            description: '🔧 Other changes (maintenance)',
            title: 'Chores',
            emoji: '🔧'
          },
          revert: {
            description: '⏪ Revert a previous commit',
            title: 'Reverts',
            emoji: '⏪'
          }
        }
      },
      scope: {
        description: 'What is the scope of this change (e.g. Core, Gateway, Docker, Cicd)'
      },
      subject: {
        description: 'Write a short, imperative tense description of the change'
      },
      body: {
        description: 'Provide a longer description of the change'
      },
      isBreaking: {
        description: 'Are there any breaking changes?'
      },
      breakingBody: {
        description: 'A BREAKING CHANGE commit requires a body. Please enter a longer description'
      },
      breaking: {
        description: 'Describe the breaking changes'
      },
      isIssueAffected: {
        description: 'Does this change affect any open issues?'
      },
      issuesBody: {
        description: 'If issues are closed, the commit requires a body. Please enter a longer description'
      },
      issues: {
        description: 'Add issue references (e.g. "fix #123", "re #456")'
      }
    }
  }
};
