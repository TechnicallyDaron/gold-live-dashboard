import { getMobilePlatform } from './platform.js'

// Each step names a route to navigate to and a data-tour selector to
// spotlight. General "here's this page" steps spotlight that page's tab in
// TabBar; steps about a specific in-page element (bell, journal, add-tile)
// spotlight that element instead. `target: null` centers the card with no
// cutout (used for the intro/finish cards).
export const TOUR_STEPS = [
  {
    id: 'hub',
    route: '/hub',
    target: '[data-tour="tab-hub"]',
    body: 'This is your command center. Every asset you track lives here as a live card — the most active ones float to the top automatically. Tap any card to dig in. Quieter names tuck into the drawer below.',
  },
  {
    id: 'bell',
    route: '/hub',
    target: '[data-tour="bell"]',
    body: "Alerts land here: trade setups from validated strategies, big movers, and warnings on your positions. If the bell rings, it's worth a look.",
  },
  {
    id: 'chart',
    route: '/chart',
    target: '[data-tour="tab-chart"]',
    body: 'Price history for any asset, with the moving averages the strategies actually use. Good for seeing the story behind a signal.',
  },
  {
    id: 'bias',
    route: '/bias',
    target: '[data-tour="tab-bias"]',
    body: "The engine's honest read on one asset: which way it leans, what would trigger a setup, and — just as important — what would prove the idea wrong.",
  },
  {
    id: 'news',
    route: '/news',
    target: '[data-tour="tab-news"]',
    body: 'Headlines for your assets with an AI read on the mood. Context, not signals.',
  },
  {
    id: 'positions',
    route: '/positions',
    target: '[data-tour="tab-positions"]',
    body: 'When you take a trade, log it here — the contract, strike, and expiration. The app then guards it: it warns you before earnings, when time is running out, and when your trade reaches its statistical target.',
  },
  {
    id: 'journal',
    route: '/positions',
    target: '[data-tour="journal"]',
    body: 'Every closed trade lands here forever: your win rate, your average result, and whether you followed your own rules. This is your honest track record — the app never forgets, so you don’t have to.',
  },
  {
    id: 'add-assets',
    route: '/hub',
    target: '[data-tour="add-tile"]',
    body: "Track anything: type a ticker and you're done. Your list is yours alone.",
  },
  {
    id: 'install',
    route: null,
    target: null,
    conditional: 'install',
    body: () =>
      getMobilePlatform() === 'ios'
        ? 'One last thing — put N-CORE on your home screen like a real app: tap the Share button (the square with the arrow) at the bottom of Safari, scroll down, and tap Add to Home Screen. Full screen, one tap away, no browser bars.'
        : 'One last thing — install N-CORE like a real app: tap the ⋮ three dots menu, then Add to Home Screen (or Install app). Full screen, one tap away.',
  },
  {
    id: 'finish',
    route: null,
    target: null,
    body: 'That’s the whole app. One rule to trade by: the alerts are invitations, not commands — size small, log honestly, and let your journal teach you. Good hunting.',
    finishLabel: 'Start exploring',
  },
]
