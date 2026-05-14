import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'PRCGAP documentation',
  description:
    'Personalized Reference genome-based Cancer Genome Analysis Pipeline — Snakemake workflow for tumor/normal long-read cancer genome analysis on phased de novo assemblies.',
  lang: 'en-US',

  // GitHub Pages base path: change to '/<repo-name>/' when deploying to
  // https://<user-or-org>.github.io/<repo-name>/. Leave as '/' if you publish
  // at the root of a custom domain.
  base: '/prcgapdoc/',

  lastUpdated: true,
  cleanUrls: true,
  ignoreDeadLinks: true,

  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Get Started', link: '/Introduction' },
      {
        text: 'GitHub',
        link: 'https://github.com/yos-sk/prcgapdoc',
      },
    ],

    sidebar: [
      {
        text: 'PRCGAP',
        items: [
          { text: 'Introduction', link: '/Introduction' },
          { text: 'Preparation', link: '/Preparation' },
          { text: 'Usage', link: '/Usage' },
          { text: 'Workflow', link: '/Workflow' },
          { text: 'Example', link: '/Example' },
        ],
      },
    ],

    search: {
      provider: 'local',
    },

    outline: {
      level: [2, 3],
      label: 'On this page',
    },

    editLink: {
      pattern:
        'https://github.com/yos-sk/prcgapdoc/edit/master/docs/:path',
      text: 'Edit this page on GitHub',
    },

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'National Cancer Center — Genome Analysis Group',
    },
  },
})
