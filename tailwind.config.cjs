module.exports = {
content: ["farmsync/static/index.html", "farmsync/static/workspace.js"],
      theme: {
        extend: {
          fontFamily: {
            sans: ['"Plus Jakarta Sans"', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'monospace'],
          },
          colors: {
            brand: {
              50: '#F0F9F4',
              100: '#DCF2E4',
              500: '#27AE60',
              600: '#1E8E4D',
              700: '#166E3A',
              800: '#11522B',
              900: '#0B381C',
            },
            navy: {
              800: '#1E293B',
              900: '#0F172A',
            }
          }
        }
      }
    };
