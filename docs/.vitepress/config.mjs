import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'PRCGAP documentation',
  description:
    'Personalized Reference genome-based Cancer Genome Analysis Pipeline: Snakemake workflow for tumor/normal long-read cancer genome analysis on phased de novo assemblies.',
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
      { text: 'Quick start', link: '/QuickStart' },
      { text: 'Options', link: '/Options' },
      {
        text: 'GitHub',
        link: 'https://github.com/yos-sk/PRCGAP',
      },
    ],

    sidebar: [
      {
        text: 'PRCGAP',
        items: [
          { text: 'Introduction', link: '/Introduction' },
          { text: 'Quick start', link: '/QuickStart' },
          { text: 'Usage', link: '/Usage' },
          { text: 'Options', link: '/Options' },
          { text: 'Preparation', link: '/Preparation' },
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
      message: 'Released under the GNU General Public License v3.0 (GPL-3.0).',
      copyright: 'National Cancer Center Research Institute, Division of Genome Analysis Platform Development',
    },
  },
})
