export const lightTheme = {
  bg: '#ffffff',
  surface: '#f8f9fa',
  surface2: '#e9ecef',
  text: '#1a1a2e',
  muted: '#6c757d',
  border: '#dee2e6',
};

export const darkTheme = {
  bg: '#0e1117',
  surface: '#161b25',
  surface2: '#1e2535',
  text: '#e2e8f4',
  muted: '#6b7a99',
  border: 'rgba(255,255,255,0.07)',
};

/**
 * HOSI Brand OS Official Color Palette
 * Source: https://hosi-brand-os.vercel.app/ (hosi.brand.json)
 */
export const hosiPalette = {
  navy: '#19272F',        // Primary spine: ground and text
  navyCard: '#233640',    // Elevated surface cards
  navyDeep: '#121D23',    // Dark background ground
  navyNight: '#0E171C',   // Deepest contrast boundary
  copper: '#D67D4A',      // Secondary charge: grounds, rules, display type
  copperDeep: '#A85A2E',  // High contrast text on light (4.60:1 on cream)
  copperLight: '#ED9A5E', // Light copper accents
  copperPale: '#F6C79C',  // Labels on navy
  cream: '#F9F4EB',       // Canvas
  creamCard: '#FCF9F2',   // Canvas surface
  sand: '#FBEAD8',        // Storefront & soft tint ground
  inkMid: '#46535B',      // Body text
  inkLight: '#7E8890',    // Subdued captions
} as const;

/**
 * Platform Core Palette
 */
export const sitaPalette = {
  blue: '#1082ff',
  blueDim: '#12325e',
  cyan: '#009bd4',
  cyanDim: '#0e3352',
  amber: '#fbbf24',
  amberDim: '#3b2e12',
  green: '#00af66',
  greenDim: '#0e3a2b',
  red: '#f87171',
  redDim: '#3b1a1a',
} as const;
