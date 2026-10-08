import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import AtomScene from './AtomScene'
import { RESOURCE_CATEGORIES } from '../data/resourceCategories'
import './PeriodicTable.css'

// ── Category colour palette (matches resource category palette) ───────────────
export const CAT_COLORS = {
  alkali:     '#f87171',
  alkaline:   '#fb923c',
  transition: '#60a5fa',
  post:       '#94a3b8',
  metalloid:  '#34d399',
  nonmetal:   '#a3e635',
  halogen:    '#facc15',
  noble:      '#4fc3f7',
  lanthanide: '#c084fc',
  actinide:   '#f472b6',
  unknown:    '#475569',
}

const CAT_LABELS = {
  alkali:     'Alkali Metals',
  alkaline:   'Alkaline Earth',
  transition: 'Transition Metals',
  post:       'Post-Transition',
  metalloid:  'Metalloids',
  nonmetal:   'Nonmetals',
  halogen:    'Halogens',
  noble:      'Noble Gases',
  lanthanide: 'Lanthanides',
  actinide:   'Actinides',
  unknown:    'Unknown',
}

// ── Element data: [atomicNumber, symbol, name, category, row, col] ────────────
// row/col refer to the standard 18-column periodic table grid.
// Lanthanides → row 9, cols 3-17 (separate f-block row)
// Actinides   → row 10, cols 3-17 (separate f-block row)
// Placeholders at row 6 col 3 (57-71) and row 7 col 3 (89-103)
const ELEMENTS = [
  [1,  'H',  'Hydrogen',      'nonmetal',   1, 1 ],
  [2,  'He', 'Helium',        'noble',       1, 18],
  [3,  'Li', 'Lithium',       'alkali',      2, 1 ],
  [4,  'Be', 'Beryllium',     'alkaline',    2, 2 ],
  [5,  'B',  'Boron',         'metalloid',   2, 13],
  [6,  'C',  'Carbon',        'nonmetal',    2, 14],
  [7,  'N',  'Nitrogen',      'nonmetal',    2, 15],
  [8,  'O',  'Oxygen',        'nonmetal',    2, 16],
  [9,  'F',  'Fluorine',      'halogen',     2, 17],
  [10, 'Ne', 'Neon',          'noble',       2, 18],
  [11, 'Na', 'Sodium',        'alkali',      3, 1 ],
  [12, 'Mg', 'Magnesium',     'alkaline',    3, 2 ],
  [13, 'Al', 'Aluminum',      'post',        3, 13],
  [14, 'Si', 'Silicon',       'metalloid',   3, 14],
  [15, 'P',  'Phosphorus',    'nonmetal',    3, 15],
  [16, 'S',  'Sulfur',        'nonmetal',    3, 16],
  [17, 'Cl', 'Chlorine',      'halogen',     3, 17],
  [18, 'Ar', 'Argon',         'noble',       3, 18],
  [19, 'K',  'Potassium',     'alkali',      4, 1 ],
  [20, 'Ca', 'Calcium',       'alkaline',    4, 2 ],
  [21, 'Sc', 'Scandium',      'transition',  4, 3 ],
  [22, 'Ti', 'Titanium',      'transition',  4, 4 ],
  [23, 'V',  'Vanadium',      'transition',  4, 5 ],
  [24, 'Cr', 'Chromium',      'transition',  4, 6 ],
  [25, 'Mn', 'Manganese',     'transition',  4, 7 ],
  [26, 'Fe', 'Iron',          'transition',  4, 8 ],
  [27, 'Co', 'Cobalt',        'transition',  4, 9 ],
  [28, 'Ni', 'Nickel',        'transition',  4, 10],
  [29, 'Cu', 'Copper',        'transition',  4, 11],
  [30, 'Zn', 'Zinc',          'transition',  4, 12],
  [31, 'Ga', 'Gallium',       'post',        4, 13],
  [32, 'Ge', 'Germanium',     'metalloid',   4, 14],
  [33, 'As', 'Arsenic',       'metalloid',   4, 15],
  [34, 'Se', 'Selenium',      'nonmetal',    4, 16],
  [35, 'Br', 'Bromine',       'halogen',     4, 17],
  [36, 'Kr', 'Krypton',       'noble',       4, 18],
  [37, 'Rb', 'Rubidium',      'alkali',      5, 1 ],
  [38, 'Sr', 'Strontium',     'alkaline',    5, 2 ],
  [39, 'Y',  'Yttrium',       'transition',  5, 3 ],
  [40, 'Zr', 'Zirconium',     'transition',  5, 4 ],
  [41, 'Nb', 'Niobium',       'transition',  5, 5 ],
  [42, 'Mo', 'Molybdenum',    'transition',  5, 6 ],
  [43, 'Tc', 'Technetium',    'transition',  5, 7 ],
  [44, 'Ru', 'Ruthenium',     'transition',  5, 8 ],
  [45, 'Rh', 'Rhodium',       'transition',  5, 9 ],
  [46, 'Pd', 'Palladium',     'transition',  5, 10],
  [47, 'Ag', 'Silver',        'transition',  5, 11],
  [48, 'Cd', 'Cadmium',       'transition',  5, 12],
  [49, 'In', 'Indium',        'post',        5, 13],
  [50, 'Sn', 'Tin',           'post',        5, 14],
  [51, 'Sb', 'Antimony',      'metalloid',   5, 15],
  [52, 'Te', 'Tellurium',     'metalloid',   5, 16],
  [53, 'I',  'Iodine',        'halogen',     5, 17],
  [54, 'Xe', 'Xenon',         'noble',       5, 18],
  [55, 'Cs', 'Cesium',        'alkali',      6, 1 ],
  [56, 'Ba', 'Barium',        'alkaline',    6, 2 ],
  // 57-71 → lanthanide f-block rows (row 9)
  [57, 'La', 'Lanthanum',     'lanthanide',  9, 3 ],
  [58, 'Ce', 'Cerium',        'lanthanide',  9, 4 ],
  [59, 'Pr', 'Praseodymium',  'lanthanide',  9, 5 ],
  [60, 'Nd', 'Neodymium',     'lanthanide',  9, 6 ],
  [61, 'Pm', 'Promethium',    'lanthanide',  9, 7 ],
  [62, 'Sm', 'Samarium',      'lanthanide',  9, 8 ],
  [63, 'Eu', 'Europium',      'lanthanide',  9, 9 ],
  [64, 'Gd', 'Gadolinium',    'lanthanide',  9, 10],
  [65, 'Tb', 'Terbium',       'lanthanide',  9, 11],
  [66, 'Dy', 'Dysprosium',    'lanthanide',  9, 12],
  [67, 'Ho', 'Holmium',       'lanthanide',  9, 13],
  [68, 'Er', 'Erbium',        'lanthanide',  9, 14],
  [69, 'Tm', 'Thulium',       'lanthanide',  9, 15],
  [70, 'Yb', 'Ytterbium',     'lanthanide',  9, 16],
  [71, 'Lu', 'Lutetium',      'lanthanide',  9, 17],
  [72, 'Hf', 'Hafnium',       'transition',  6, 4 ],
  [73, 'Ta', 'Tantalum',      'transition',  6, 5 ],
  [74, 'W',  'Tungsten',      'transition',  6, 6 ],
  [75, 'Re', 'Rhenium',       'transition',  6, 7 ],
  [76, 'Os', 'Osmium',        'transition',  6, 8 ],
  [77, 'Ir', 'Iridium',       'transition',  6, 9 ],
  [78, 'Pt', 'Platinum',      'transition',  6, 10],
  [79, 'Au', 'Gold',          'transition',  6, 11],
  [80, 'Hg', 'Mercury',       'transition',  6, 12],
  [81, 'Tl', 'Thallium',      'post',        6, 13],
  [82, 'Pb', 'Lead',          'post',        6, 14],
  [83, 'Bi', 'Bismuth',       'post',        6, 15],
  [84, 'Po', 'Polonium',      'post',        6, 16],
  [85, 'At', 'Astatine',      'halogen',     6, 17],
  [86, 'Rn', 'Radon',         'noble',       6, 18],
  [87, 'Fr', 'Francium',      'alkali',      7, 1 ],
  [88, 'Ra', 'Radium',        'alkaline',    7, 2 ],
  // 89-103 → actinide f-block rows (row 10)
  [89, 'Ac', 'Actinium',      'actinide',    10, 3 ],
  [90, 'Th', 'Thorium',       'actinide',    10, 4 ],
  [91, 'Pa', 'Protactinium',  'actinide',    10, 5 ],
  [92, 'U',  'Uranium',       'actinide',    10, 6 ],
  [93, 'Np', 'Neptunium',     'actinide',    10, 7 ],
  [94, 'Pu', 'Plutonium',     'actinide',    10, 8 ],
  [95, 'Am', 'Americium',     'actinide',    10, 9 ],
  [96, 'Cm', 'Curium',        'actinide',    10, 10],
  [97, 'Bk', 'Berkelium',     'actinide',    10, 11],
  [98, 'Cf', 'Californium',   'actinide',    10, 12],
  [99, 'Es', 'Einsteinium',   'actinide',    10, 13],
  [100,'Fm', 'Fermium',       'actinide',    10, 14],
  [101,'Md', 'Mendelevium',   'actinide',    10, 15],
  [102,'No', 'Nobelium',      'actinide',    10, 16],
  [103,'Lr', 'Lawrencium',    'actinide',    10, 17],
  [104,'Rf', 'Rutherfordium', 'transition',  7, 4 ],
  [105,'Db', 'Dubnium',       'transition',  7, 5 ],
  [106,'Sg', 'Seaborgium',    'transition',  7, 6 ],
  [107,'Bh', 'Bohrium',       'transition',  7, 7 ],
  [108,'Hs', 'Hassium',       'transition',  7, 8 ],
  [109,'Mt', 'Meitnerium',    'unknown',     7, 9 ],
  [110,'Ds', 'Darmstadtium',  'unknown',     7, 10],
  [111,'Rg', 'Roentgenium',   'unknown',     7, 11],
  [112,'Cn', 'Copernicium',   'transition',  7, 12],
  [113,'Nh', 'Nihonium',      'unknown',     7, 13],
  [114,'Fl', 'Flerovium',     'unknown',     7, 14],
  [115,'Mc', 'Moscovium',     'unknown',     7, 15],
  [116,'Lv', 'Livermorium',   'unknown',     7, 16],
  [117,'Ts', 'Tennessine',    'unknown',     7, 17],
  [118,'Og', 'Oganesson',     'unknown',     7, 18],
]

// Build a grid lookup: `${row}-${col}` → element tuple
const GRID = {}
ELEMENTS.forEach(el => { GRID[`${el[4]}-${el[5]}`] = el })

// ── Element cell ──────────────────────────────────────────────────────────────
function ElCell({ el, small = false, onClick }) {
  if (!el) return null
  const [n, sym, name, cat] = el
  const color = CAT_COLORS[cat] ?? CAT_COLORS.unknown
  return (
    <div
      className={`pt-cell${small ? ' pt-cell--sm' : ''}${onClick ? ' pt-cell--clickable' : ''}`}
      title={`${n} — ${name}`}
      onClick={onClick}
      style={{
        borderColor: `${color}55`,
        background:  `${color}1E`,
        '--hover-bg': `${color}3C`,
      }}
    >
      <span className="pt-num">{n}</span>
      <span className="pt-sym">{sym}</span>
      <span className="pt-name">{name.length > 11 ? name.slice(0, 10) + '…' : name}</span>
    </div>
  )
}

// ── Large element card (used in profile view) ─────────────────────────────────
function ElCardLarge({ el }) {
  const [n, sym, name, cat] = el
  const color = CAT_COLORS[cat] ?? CAT_COLORS.unknown
  return (
    <div
      className="pt-el-card-lg"
      style={{ borderColor: `${color}66`, background: `${color}22` }}
    >
      <span className="pt-el-card-lg__num">{n}</span>
      <span className="pt-el-card-lg__sym">{sym}</span>
      <span className="pt-el-card-lg__name">{name}</span>
    </div>
  )
}

// ── Materials lookup: symbol → [{ name, cat, desc }] ─────────────────────────
const MATERIALS_BY_SYMBOL = {
  H:  [
    { name: 'Water (H₂O)',         cat: 'Compound',      desc: 'Universal solvent; essential for all known life' },
    { name: 'Hydrogen Fuel',        cat: 'Energy',        desc: 'Zero-emission fuel for cells and combustion engines' },
    { name: 'Ammonia (NH₃)',        cat: 'Compound',      desc: 'Primary fertiliser feedstock; also a refrigerant' },
  ],
  Li: [
    { name: 'Li-Ion Battery',       cat: 'Energy',        desc: 'Dominant rechargeable battery chemistry for EVs and consumer electronics' },
    { name: 'LFP Battery',          cat: 'Energy',        desc: 'Lithium iron phosphate — long-cycle, thermally stable cells' },
    { name: 'Lithium Carbonate',    cat: 'Compound',      desc: 'Battery precursor and psychiatric medication' },
  ],
  C:  [
    { name: 'Steel',                cat: 'Alloy',         desc: 'Iron-carbon alloy; the most widely used structural metal' },
    { name: 'Carbon Fibre',         cat: 'Composite',     desc: 'Exceptional strength-to-weight ratio for aerospace and sport' },
    { name: 'Diamond',              cat: 'Mineral',       desc: 'Hardest natural material; used in cutting tools and gems' },
    { name: 'Graphene',             cat: 'Nanomaterial',  desc: 'Single-atom carbon lattice with extraordinary conductivity' },
    { name: 'Carbon Black',         cat: 'Industrial',    desc: 'Pigment and reinforcing filler in rubber and inks' },
  ],
  Si: [
    { name: 'Silicon Wafer',        cat: 'Semiconductor', desc: 'Substrate for virtually all integrated circuits' },
    { name: 'Silicon Carbide (SiC)',cat: 'Ceramic',       desc: 'Abrasives and wide-bandgap power electronics' },
    { name: 'Silicon Nitride',      cat: 'Ceramic',       desc: 'High-temperature structural ceramic for bearings and turbines' },
    { name: 'Glass',                cat: 'Amorphous',     desc: 'SiO₂-based; optics, windows, and optical fibres' },
  ],
  Fe: [
    { name: 'Steel',                cat: 'Alloy',         desc: 'Iron + carbon; backbone of construction and manufacturing' },
    { name: 'Stainless Steel',      cat: 'Alloy',         desc: 'Fe-Cr-Ni; corrosion-resistant metal for kitchens and industry' },
    { name: 'Cast Iron',            cat: 'Alloy',         desc: 'High-carbon iron; cookware, pipes, and engine blocks' },
    { name: 'Ferrite',              cat: 'Ceramic',       desc: 'Iron-oxide ceramic for transformer cores and magnets' },
  ],
  Cu: [
    { name: 'Brass',                cat: 'Alloy',         desc: 'Cu-Zn alloy; fittings, valves, and musical instruments' },
    { name: 'Bronze',               cat: 'Alloy',         desc: 'Cu-Sn alloy; bearings, sculpture, and coinage' },
    { name: 'Copper Wire',          cat: 'Conductor',     desc: 'Primary electrical conductor in wiring and motors' },
    { name: 'Cupronickel',          cat: 'Alloy',         desc: 'Cu-Ni alloy; coinage and marine engineering' },
  ],
  Ni: [
    { name: 'Inconel',              cat: 'Superalloy',    desc: 'Ni-Cr superalloy for jet engines and gas turbines' },
    { name: 'Stainless Steel',      cat: 'Alloy',         desc: 'Fe-Cr-Ni; Ni gives corrosion resistance and toughness' },
    { name: 'NiMH Battery',         cat: 'Energy',        desc: 'Nickel-metal hydride; hybrid vehicle battery packs' },
    { name: 'Nickel Silver',        cat: 'Alloy',         desc: 'Cu-Ni-Zn; silverware, zippers, and musical keys' },
  ],
  Al: [
    { name: 'Duralumin',            cat: 'Alloy',         desc: 'Al-Cu alloy; aerospace structural panels and ribs' },
    { name: 'Al-Si Alloy',          cat: 'Alloy',         desc: 'Casting alloy for automotive engine components' },
    { name: 'Alumina (Al₂O₃)',     cat: 'Ceramic',       desc: 'Abrasive, refractory liner, and electronic substrate' },
    { name: 'Aluminium Foil',       cat: 'Product',       desc: 'Packaging barrier and thermal insulation wrap' },
  ],
  Ti: [
    { name: 'Ti-6Al-4V',           cat: 'Alloy',         desc: 'Workhorse titanium alloy for aerospace and medical implants' },
    { name: 'Titanium Dioxide',     cat: 'Compound',      desc: 'TiO₂; white pigment in paint, paper, and sunscreen' },
    { name: 'TiN Coating',          cat: 'Coating',       desc: 'Hard golden-coloured physical vapour deposition coating for tools' },
  ],
  Cr: [
    { name: 'Stainless Steel',      cat: 'Alloy',         desc: 'Cr is the defining element; passivates the steel surface' },
    { name: 'Chrome Plating',       cat: 'Coating',       desc: 'Decorative and hard-chrome coatings for corrosion protection' },
    { name: 'Nichrome',             cat: 'Alloy',         desc: 'Ni-Cr resistance wire for heaters and toasters' },
  ],
  Mn: [
    { name: 'Steel',                cat: 'Alloy',         desc: 'Mn deoxidises steel and boosts hardenability' },
    { name: 'MnO₂ Battery',        cat: 'Energy',        desc: 'Alkaline cell cathode; widest-used primary battery' },
  ],
  Co: [
    { name: 'Li-Ion (LCO) Battery', cat: 'Energy',        desc: 'Lithium cobalt oxide cathode; highest energy density' },
    { name: 'Stellite',             cat: 'Superalloy',    desc: 'Co-Cr-W; wear-resistant cutting tools and valve seats' },
    { name: 'Samarium Cobalt',      cat: 'Magnet',        desc: 'SmCo permanent magnets for high-temperature motors' },
  ],
  Zn: [
    { name: 'Galvanised Steel',     cat: 'Coating',       desc: 'Hot-dip zinc coating for corrosion protection of structural steel' },
    { name: 'Brass',                cat: 'Alloy',         desc: 'Cu-Zn alloy; plumbing fittings and musical instruments' },
    { name: 'Zamak',                cat: 'Alloy',         desc: 'Zn-Al die-cast alloy for precision hardware components' },
  ],
  Mo: [
    { name: 'HSLA Steel',           cat: 'Alloy',         desc: 'Mo raises hardenability and creep strength in structural steels' },
    { name: 'MoS₂',               cat: 'Lubricant',     desc: 'Molybdenum disulfide dry lubricant for high-vacuum applications' },
  ],
  W:  [
    { name: 'Tungsten Carbide',     cat: 'Cermet',        desc: 'WC-Co; the hardest cutting tool material for machining' },
    { name: 'Tungsten Wire',        cat: 'Conductor',     desc: 'Incandescent lamp filaments and X-ray tube anodes' },
    { name: 'High-Speed Steel',     cat: 'Alloy',         desc: 'W-Mo tool steel for drills, taps, and end mills' },
  ],
  Pb: [
    { name: 'Lead-Acid Battery',    cat: 'Energy',        desc: 'SLI starter batteries; oldest rechargeable chemistry' },
    { name: 'Solder (Pb-Sn)',       cat: 'Alloy',         desc: 'Traditional tin-lead electronics joining alloy' },
    { name: 'Lead Glass',           cat: 'Amorphous',     desc: 'PbO glass for radiation shielding and precision optics' },
  ],
  Sn: [
    { name: 'SAC Solder',           cat: 'Alloy',         desc: 'Sn-Ag-Cu lead-free solder for PCB assembly' },
    { name: 'Bronze',               cat: 'Alloy',         desc: 'Cu-Sn alloy; bearings, bells, and marine hardware' },
    { name: 'Tinplate',             cat: 'Coating',       desc: 'Sn-coated steel sheet for food and beverage cans' },
  ],
  V:  [
    { name: 'Vanadium Steel',       cat: 'Alloy',         desc: 'V micro-alloying for high-strength tools, springs, and gears' },
    { name: 'Vanadium Flow Battery',cat: 'Energy',        desc: 'Grid-scale redox flow storage for renewable energy' },
  ],
  Nd: [
    { name: 'NdFeB Magnet',         cat: 'Magnet',        desc: 'Strongest permanent magnets; essential for EV motors and wind turbines' },
  ],
  Ag: [
    { name: 'Sterling Silver',      cat: 'Alloy',         desc: '92.5% Ag + Cu; jewellery and silverware' },
    { name: 'Silver Solder',        cat: 'Alloy',         desc: 'High-strength brazing filler for copper plumbing and HVAC' },
    { name: 'Silver Oxide Battery', cat: 'Energy',        desc: 'High-voltage coin cell for watches and precision instruments' },
  ],
  Au: [
    { name: 'Gold Alloys',          cat: 'Alloy',         desc: '18k/14k gold with Cu, Ag, Pd for jewellery durability' },
    { name: 'Gold Bond Wire',       cat: 'Conductor',     desc: 'Corrosion-free ultrafine wire for IC die bonding' },
  ],
  Pt: [
    { name: 'Catalytic Converter',  cat: 'Catalyst',      desc: 'Pt/Pd/Rh catalyst bed for exhaust emission control' },
    { name: 'PEM Fuel Cell',        cat: 'Energy',        desc: 'Pt-based electrode catalysts for hydrogen fuel cells' },
    { name: 'Pt-Ir Alloy',          cat: 'Alloy',         desc: 'Platinum-iridium; lab standards and spark plug tips' },
  ],
  Pd: [
    { name: 'Catalytic Converter',  cat: 'Catalyst',      desc: 'Pd is the primary catalyst for petrol engine converters' },
    { name: 'Palladium Hydrogen',   cat: 'Storage',       desc: 'Pd absorbs hydrogen at high density for storage research' },
  ],
}

// Category badge colours for material science cards
const MAT_CAT_COLORS = {
  Alloy: '#60a5fa', Compound: '#a3e635', Ceramic: '#fb923c',
  Energy: '#34d399', Semiconductor: '#4fc3f7', Composite: '#c084fc',
  Nanomaterial: '#f472b6', Coating: '#94a3b8', Conductor: '#facc15',
  Industrial: '#64748b', Lubricant: '#78716c', Superalloy: '#f87171',
  Magnet: '#e879f9', Catalyst: '#2dd4bf', Cermet: '#fb7185',
  Amorphous: '#67e8f9', Product: '#fbbf24', Storage: '#6ee7b7',
  Mineral: '#a78bfa',
}

// ── Resource element descriptions: what it is + what it's used for ────────────
const RESOURCE_ELEMENT_DESCRIPTIONS = {
  Au: { what: 'Dense, noble yellow metal highly resistant to corrosion and tarnish.', uses: 'Jewelry, electrical contacts, dentistry, monetary reserves, and nano-medicine.' },
  Ag: { what: 'Softest precious metal with the highest electrical and thermal conductivity of any element.', uses: 'Electronics, solar cells, photography, antimicrobial coatings, and jewelry.' },
  Pt: { what: 'Dense, malleable, silvery-white metal of extraordinary corrosion resistance.', uses: 'Catalytic converters, hydrogen fuel cells, jewelry, laboratory equipment, and cancer drugs.' },
  Pd: { what: 'Rare silvery-white metal that can absorb up to 900 times its own volume of hydrogen.', uses: 'Catalytic converters for petrol engines, hydrogen purification, electronics, and dental alloys.' },
  Rh: { what: 'Rarest platinum-group metal; extremely hard, reflective, and resistant to corrosion.', uses: 'Three-way catalytic converters, reflective coatings for mirrors, and hardening platinum alloys.' },
  Ru: { what: 'Hard, silvery transition metal with high melting point and chemical stability.', uses: 'Hard disk drive coatings, electrical contacts, catalyst in chemical synthesis, and fuel-cell electrodes.' },
  Ir: { what: 'Densest naturally occurring element; among the most corrosion-resistant metals known.', uses: 'Spark plug tips, fountain pen nibs, satellite thrusters, crucibles, and platinum hardening.' },
  Os: { what: 'Densest naturally occurring element (tied with Ir); brittle, blue-grey metal with a pungent oxide.', uses: 'Electron microscopy staining, fountain pen tips, electrical contacts, and hardening alloys.' },

  Cu: { what: 'Ductile, reddish metal with the second-highest electrical conductivity of any element.', uses: 'Electrical wiring, plumbing, motors, heat exchangers, and alloys such as brass and bronze.' },
  Fe: { what: "Most abundant metal in Earth's crust; the backbone of industrial civilisation.", uses: 'Steel for construction, vehicles, machinery, appliances, and infrastructure worldwide.' },
  Ni: { what: 'Hard, ductile, silvery-white ferromagnetic metal with strong corrosion resistance.', uses: 'Stainless steel, superalloys for jet engines, rechargeable batteries, and electroplating.' },
  Zn: { what: 'Bluish-white metal that naturally resists corrosion through a self-protective oxide layer.', uses: 'Galvanizing steel, die-casting, brass alloys, sunscreen, and dietary supplements.' },
  Pb: { what: 'Dense, soft, highly malleable metal with a very low melting point.', uses: 'Lead-acid batteries, radiation shielding, ammunition, and historically in solder and pigments.' },
  Al: { what: "Lightweight, corrosion-resistant silvery metal and the most abundant metal in Earth's crust.", uses: 'Aerospace structures, packaging, construction, electrical transmission lines, and transport.' },
  Sn: { what: 'Silvery, malleable metal resistant to corrosion at room temperature.', uses: 'Solder for electronics, tin-plate for food cans, bronze alloys, and specialty glass coatings.' },
  Co: { what: 'Hard, lustrous, bluish-grey ferromagnetic metal with a high melting point.', uses: 'Lithium-ion battery cathodes, jet-engine superalloys, permanent magnets, and blue pigments.' },

  La: { what: 'Soft, silvery-white rare earth metal that oxidises rapidly in air.', uses: 'Nickel-metal hydride batteries, camera lenses, petroleum cracking catalysts, and arc lighting.' },
  Ce: { what: 'Most abundant rare earth; yellowish-grey metal that ignites easily when scratched.', uses: 'Catalytic converters, glass polishing, self-cleaning ovens, UV-blocking glass, and diesel additives.' },
  Nd: { what: 'Bright, silvery rare earth metal with strong magnetic properties.', uses: 'NdFeB permanent magnets — the world\'s strongest — for EV motors, wind turbines, and headphones.' },
  Pr: { what: 'Soft, silvery, slightly yellowish rare earth with notable magnetic properties.', uses: 'NdFeB magnet alloying, high-strength aircraft engine alloys, and specialised glass colouring.' },
  Dy: { what: 'Rare earth with the highest magnetic strength per atom; critical in high-temperature magnets.', uses: 'Improving high-temperature performance and coercivity of NdFeB magnets for EVs and wind turbines.' },
  Sm: { what: 'Moderately hard, silvery rare earth with stable high-temperature magnetic properties.', uses: 'SmCo permanent magnets for high-temperature motors, sensors, headphones, and defense systems.' },
  Gd: { what: 'Silvery-white rare earth with unique neutron-absorption and paramagnetic properties.', uses: 'MRI contrast agents, nuclear reactor control rods, and green phosphors in display screens.' },
  Tb: { what: 'Silvery-white rare earth that fluoresces bright green under UV light.', uses: 'Green phosphors in LED lighting, solid-state devices, fuel cell membranes, and magneto-optical films.' },
  Y:  { what: 'Silvery transition metal often classified with rare earths due to similar chemistry.', uses: 'LED and display phosphors, YAG lasers, camera lenses, and superconductor compounds.' },

  Li: { what: 'Lightest metal and least dense solid element; highly reactive alkali metal.', uses: 'Li-ion and LFP batteries for EVs and electronics, mood-stabilizing medication, and lubricant greases.' },
  Mn: { what: 'Hard, brittle, greyish-white transition metal essential to steel production.', uses: 'Steel hardening and deoxidation, alkaline battery cathodes, aluminium alloys, and fertilizers.' },
  C:  { what: 'Non-metal that forms more compounds than any other element; basis of all organic chemistry.', uses: 'Graphite electrodes in batteries, carbon fibre composites, steel production, nuclear moderators, and diamonds.' },

  Cr: { what: 'Hard, lustrous, steel-grey transition metal with exceptional corrosion resistance.', uses: 'Stainless steel, hard chrome plating, chrome pigments, and catalytic chemical processes.' },
  Ti: { what: 'Lightweight, strong, silver-coloured metal with extraordinary corrosion resistance.', uses: 'Aerospace structures, medical implants, naval hardware, and titanium dioxide (TiO₂) white pigment.' },
  V:  { what: 'Hard, silvery-grey metal that significantly strengthens steel at low concentrations.', uses: 'High-strength tool steels, vanadium redox flow batteries for grid storage, and catalysts.' },
  Mo: { what: 'Silvery, refractory metal with one of the highest melting points of any metal.', uses: 'Steel and superalloy strengthening, MoS₂ dry lubricant, catalysts in petroleum refining, and electronics.' },
  W:  { what: 'Dense, grey metal with the highest melting point of any pure metal (3,422 °C).', uses: 'Tungsten carbide cutting tools, incandescent lamp filaments, X-ray tube anodes, and high-speed steel.' },
  P:  { what: 'Highly reactive non-metal essential to all life as a component of DNA and cell membranes.', uses: 'Fertilizers (phosphate rock), matches, flame retardants, detergents, and food preservatives.' },
  K:  { what: 'Soft, silvery-white alkali metal that reacts violently with water.', uses: 'Potash fertilizers, potassium chloride in salt substitutes, gunpowder, and soap making.' },
  B:  { what: 'Hard, black metalloid with a very high melting point and strong covalent bonding.', uses: 'Borosilicate glass, semiconductor dopant, nuclear reactor neutron absorber, and boron-steel hardening.' },

  Nb: { what: 'Soft, grey, ductile transition metal with excellent superconducting properties at low temperatures.', uses: 'High-strength low-alloy (HSLA) steels, superconducting magnets, and jet engine alloys.' },
  Ta: { what: 'Dense, hard, blue-grey metal with the second-highest melting point of any element.', uses: 'Capacitors for smartphones and electronics, surgical implants, jet engine blades, and corrosion-resistant equipment.' },
  In: { what: "Soft, silvery-white post-transition metal that makes a distinctive squeal when bent.", uses: 'Indium tin oxide (ITO) for LCD and touchscreens, thin-film solar cells, and semiconductor coatings.' },
  Ga: { what: 'Silvery metal with an unusually low melting point — it melts in the palm of your hand.', uses: 'GaAs semiconductors, GaN for LEDs and 5G amplifiers, and solar cells.' },
  Ge: { what: 'Brittle, lustrous grey metalloid and one of the first practical semiconductors.', uses: 'Fiber optic cables, infrared optics and night-vision devices, and thin-film solar cells.' },
  Re: { what: 'Rare, dense, silvery-white metal with the third-highest melting point of any element.', uses: 'Nickel superalloy turbine blades in jet engines, catalysts in oil refining, and high-temperature wires.' },
  Te: { what: 'Brittle, mildly toxic metalloid with properties between metals and non-metals.', uses: 'CdTe thin-film solar panels, thermoelectric devices, and additives to improve steel machinability.' },
  Se: { what: 'Non-metal with photovoltaic and photoconductive properties; an essential trace element in biology.', uses: 'Thin-film solar cells, glass colorants, semiconductors, photocopier drums, and nutritional supplements.' },
}

// ── Build symbol → element lookup for the category view ──────────────────────
const ELEMENT_BY_SYMBOL = {}
ELEMENTS.forEach(el => { ELEMENT_BY_SYMBOL[el[1]] = el })

// ── Category list view (shown when no category is pre-selected) ───────────────
function CategoryList({ onSelect }) {
  return (
    <div className="pt-catlist">
      <div className="pt-catlist-hd">
        Select a resource category to explore its elements
      </div>
      <div className="pt-catlist-grid">
        {RESOURCE_CATEGORIES.map(cat => (
          <button
            key={cat.id}
            className="pt-catlist-tile"
            style={{ '--cat-color': cat.color }}
            onClick={() => onSelect(cat.id)}
          >
            <div className="pt-catlist-tile-header">
              <span className="pt-catlist-dot" style={{ background: cat.color }} />
              <span className="pt-catlist-label" style={{ color: cat.color }}>{cat.label}</span>
              {cat.phase === 2 && <span className="pt-catlist-phase">EIA live</span>}
            </div>
            <span className="pt-catlist-desc">{cat.description}</span>
            <div className="pt-catlist-syms">
              {cat.symbols.slice(0, 7).map(sym => (
                <span key={sym} className="pt-catlist-sym">{sym}</span>
              ))}
              {cat.symbols.length > 7 && (
                <span className="pt-catlist-sym pt-catlist-sym--more">+{cat.symbols.length - 7}</span>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Category detail view ──────────────────────────────────────────────────────
function CategoryDetail({ categoryId, onBack, onOpenElement }) {
  const cat = RESOURCE_CATEGORIES.find(c => c.id === categoryId)
  if (!cat) return null

  const elements = cat.symbols.map(sym => ELEMENT_BY_SYMBOL[sym]).filter(Boolean)

  return (
    <div className="pt-catdetail">
      <div className="pt-catdetail-topbar">
        <button className="pt-catdetail-back" onClick={onBack}>
          <svg width="12" height="10" viewBox="0 0 12 10" fill="none">
            <path d="M5 1L1 5l4 4M1 5h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          All categories
        </button>
        <div className="pt-catdetail-title">
          <span className="pt-catdetail-dot" style={{ background: cat.color }} />
          <span style={{ color: cat.color }}>{cat.label}</span>
          {cat.phase === 2 && <span className="pt-catlist-phase">EIA live</span>}
        </div>
        <span className="pt-catdetail-subdesc">{cat.description}</span>
      </div>

      <div className="pt-catdetail-grid">
        {elements.map(el => {
          const [n, sym, name, elCat] = el
          const elColor = CAT_COLORS[elCat] ?? CAT_COLORS.unknown
          const desc = RESOURCE_ELEMENT_DESCRIPTIONS[sym]
          return (
            <div key={n} className="pt-el-desc-card" style={{ '--el-color': elColor }}>
              <div className="pt-el-desc-card-header">
                <div
                  className="pt-el-desc-mini"
                  style={{ borderColor: `${elColor}55`, background: `${elColor}18` }}
                >
                  <span className="pt-el-desc-mini-num">{n}</span>
                  <span className="pt-el-desc-mini-sym" style={{ color: elColor }}>{sym}</span>
                  <span className="pt-el-desc-mini-name">{name}</span>
                </div>
                <button
                  className="pt-el-desc-open"
                  style={{ color: elColor, borderColor: `${elColor}44` }}
                  onClick={() => onOpenElement(el)}
                  title={`Open ${name} profile`}
                >
                  View →
                </button>
              </div>
              {desc ? (
                <>
                  <p className="pt-el-desc-what">{desc.what}</p>
                  <p className="pt-el-desc-uses">
                    <span className="pt-el-desc-uses-label">Used for: </span>
                    {desc.uses}
                  </p>
                </>
              ) : (
                <p className="pt-el-desc-what pt-el-desc-what--empty">Description coming soon.</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Element profile subtabs ───────────────────────────────────────────────────
const EL_SUBTABS = [
  { id: 'overview',          label: 'Overview'          },
  { id: 'material-science',  label: 'Material Science'  },
  { id: 'scarcity',          label: 'Scarcity'          },
]

// ── Element profile panel ─────────────────────────────────────────────────────
function ElementProfile({ el }) {
  const [subTab, setSubTab] = useState('overview')
  const [n, sym, name, cat, row, col] = el
  const color = CAT_COLORS[cat] ?? CAT_COLORS.unknown
  const isLanthanide = cat === 'lanthanide'
  const isActinide   = cat === 'actinide'
  const period = isLanthanide ? 6 : isActinide ? 7 : row
  const group  = (isLanthanide || isActinide) ? '—' : col

  const props = [
    { label: 'Atomic Number', value: n },
    { label: 'Symbol',        value: sym,   color },
    { label: 'Element Name',  value: name },
    { label: 'Category',      value: CAT_LABELS[cat], color },
    { label: 'Period',        value: period },
    { label: 'Group',         value: group },
    ...(isLanthanide ? [{ label: 'Series', value: 'Lanthanide (f-block)' }] : []),
    ...(isActinide   ? [{ label: 'Series', value: 'Actinide (f-block)'   }] : []),
  ]

  return (
    <div className="pt-el-wrap">

      {/* ── Subtab bar ── */}
      <div className="pt-subtabs" style={{ '--sub-color': color }}>
        {EL_SUBTABS.map(t => (
          <button
            key={t.id}
            className={`pt-subtab${subTab === t.id ? ' pt-subtab--active' : ''}`}
            onClick={() => setSubTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Scrollable body ── */}
      <div className="pt-el-body">

        {/* ── Overview ── */}
        {subTab === 'overview' && (<>
          {/* Top row: card + meta + animation */}
          <div className="pt-el-profile">
            <ElCardLarge el={el} />
            <div className="pt-el-profile-meta">
              <div className="pt-el-cat-badge" style={{ color, borderColor: `${color}44`, background: `${color}1A` }}>
                <span className="pt-el-cat-dot" style={{ background: color }} />
                {CAT_LABELS[cat]}
              </div>
              <div className="pt-el-props">
                {props.map(p => (
                  <div key={p.label} className="pt-el-prop">
                    <span className="pt-el-prop-label">{p.label}</span>
                    <span className="pt-el-prop-value" style={p.color ? { color: p.color } : {}}>
                      {p.value}
                    </span>
                  </div>
                ))}
              </div>
              <p className="pt-el-coming-soon">
                Atomic mass · electron configuration · natural occurrence — coming soon
              </p>
            </div>
            <div className="pt-el-anim-box">
              <span className="pt-el-anim-label">Bohr Model</span>
              <AtomScene atomicNum={n} period={period} color={color} />
            </div>
          </div>

          {/* Description section */}
          <div className="pt-el-section">
            <div className="pt-el-section-hd">
              <span className="pt-el-section-title" style={{ color }}>Description</span>
            </div>
            <p className="pt-el-desc-body">
              Detailed description of {name} — discovery history, natural occurrence,
              isotopes, electron configuration, and key chemical behaviour — coming soon.
            </p>
          </div>

          {/* News section */}
          <div className="pt-el-section">
            <div className="pt-el-section-hd">
              <span className="pt-el-section-title" style={{ color }}>News</span>
              <span className="pt-el-section-badge">live feed coming soon</span>
            </div>
            <div className="pt-news-list">
              {[
                { title: `New research on ${name} applications in advanced materials`,   source: 'Nature Materials',    date: 'May 2026' },
                { title: `${name} supply chain analysis: global production trends`,      source: 'Mining Weekly',       date: 'Apr 2026' },
                { title: `Breakthrough in ${sym}-based catalysis for green chemistry`,   source: 'Chemical & Engineering News', date: 'Mar 2026' },
              ].map((item, i) => (
                <div key={i} className="pt-news-item">
                  <span className="pt-news-dot" style={{ background: color }} />
                  <div className="pt-news-body">
                    <span className="pt-news-title">{item.title}</span>
                    <span className="pt-news-meta">{item.source} · {item.date}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>)}

        {/* ── Material Science ── */}
        {subTab === 'material-science' && (() => {
          const materials = MATERIALS_BY_SYMBOL[sym] ?? []
          return (
            <div className="pt-el-section pt-el-section--first">
              <div className="pt-el-section-hd">
                <span className="pt-el-section-title" style={{ color }}>
                  Materials containing {sym}
                </span>
                {materials.length > 0 && (
                  <span className="pt-el-section-count">{materials.length}</span>
                )}
              </div>
              {materials.length === 0 ? (
                <div className="pt-subtab-placeholder" style={{ minHeight: 200 }}>
                  <span className="pt-subtab-ph-icon">🔬</span>
                  <span className="pt-subtab-ph-title">No materials listed yet for {name}</span>
                  <span className="pt-subtab-ph-body">
                    Crystal structure · physical properties · industrial applications — coming soon
                  </span>
                </div>
              ) : (
                <div className="pt-materials-list">
                  {materials.map((m, i) => {
                    const mc = MAT_CAT_COLORS[m.cat] ?? '#64748b'
                    return (
                      <div key={i} className="pt-material-card">
                        <div className="pt-material-card-top">
                          <span className="pt-material-name">{m.name}</span>
                          <span className="pt-material-cat-badge" style={{ color: mc, borderColor: `${mc}55`, background: `${mc}18` }}>
                            {m.cat}
                          </span>
                        </div>
                        <span className="pt-material-desc">{m.desc}</span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })()}

        {/* ── Scarcity ── */}
        {subTab === 'scarcity' && (
          <div className="pt-subtab-placeholder">
            <span className="pt-subtab-ph-icon">🌍</span>
            <span className="pt-subtab-ph-title">Scarcity by Country &amp; Region</span>
            <span className="pt-subtab-ph-body">
              Global reserves · top producing nations · import dependency · supply-chain
              risk index · price volatility — coming soon
            </span>
          </div>
        )}

      </div>

    </div>
  )
}

// ── Tab definitions ───────────────────────────────────────────────────────────
const TABS = [
  { id: 'table',      label: 'Periodic Table' },
  { id: 'category',   label: 'By Category'    },
  { id: 'property',   label: 'By Property'    },
  { id: 'statistics', label: 'Statistics'     },
]

// ── Periodic Table overlay ────────────────────────────────────────────────────
export default function PeriodicTable({ onClose, initialView = { mode: 'table' } }) {
  const [activeTab, setActiveTab] = useState(() => {
    if (initialView.mode === 'category') return 'category'
    if (initialView.mode === 'element') {
      const el = ELEMENTS.find(e => e[1] === initialView.symbol)
      return el ? `el-${el[0]}` : 'table'
    }
    return 'table'
  })

  const [elementTabs, setElementTabs] = useState(() => {
    if (initialView.mode === 'element') {
      const el = ELEMENTS.find(e => e[1] === initialView.symbol)
      return el ? [el] : []
    }
    return []
  })

  const [activeCategoryId, setActiveCategoryId] = useState(
    initialView.mode === 'category' ? (initialView.categoryId ?? null) : null
  )

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  function openElementTab(el) {
    const n = el[0]
    setElementTabs(prev => prev.find(e => e[0] === n) ? prev : [...prev, el])
    setActiveTab(`el-${n}`)
  }

  function closeElementTab(n) {
    setElementTabs(prev => {
      const remaining = prev.filter(e => e[0] !== n)
      setActiveTab(cur => {
        if (cur !== `el-${n}`) return cur
        return remaining.length > 0 ? `el-${remaining[remaining.length - 1][0]}` : 'table'
      })
      return remaining
    })
  }

  // ── Build main grid cells (7 periods × 18 groups) ──────────────────────────
  const mainCells = []
  for (let row = 1; row <= 7; row++) {
    for (let col = 1; col <= 18; col++) {
      const key = `${row}-${col}`

      // Lanthanide placeholder
      if (row === 6 && col === 3) {
        mainCells.push(
          <div key={key} className="pt-cell pt-cell--placeholder"
            style={{ borderColor: `${CAT_COLORS.lanthanide}55`, background: `${CAT_COLORS.lanthanide}1E` }}>
            <span className="pt-ph-label" style={{ color: CAT_COLORS.lanthanide }}>57–71</span>
          </div>
        )
        continue
      }
      // Actinide placeholder
      if (row === 7 && col === 3) {
        mainCells.push(
          <div key={key} className="pt-cell pt-cell--placeholder"
            style={{ borderColor: `${CAT_COLORS.actinide}55`, background: `${CAT_COLORS.actinide}1E` }}>
            <span className="pt-ph-label" style={{ color: CAT_COLORS.actinide }}>89–103</span>
          </div>
        )
        continue
      }

      const el = GRID[key]
      if (!el) {
        mainCells.push(<div key={key} className="pt-cell pt-cell--empty" />)
      } else {
        mainCells.push(<ElCell key={key} el={el} onClick={() => openElementTab(el)} />)
      }
    }
  }

  // ── Build f-block rows (cols 3–17, rows 9 and 10) ──────────────────────────
  function buildFRow(row) {
    const cells = []
    cells.push(<div key={`${row}-s1`} className="pt-cell pt-cell--empty" />)
    cells.push(<div key={`${row}-s2`} className="pt-cell pt-cell--empty" />)
    for (let col = 3; col <= 17; col++) {
      const el = GRID[`${row}-${col}`]
      cells.push(<ElCell key={`${row}-${col}`} el={el} small onClick={el ? () => openElementTab(el) : undefined} />)
    }
    cells.push(<div key={`${row}-s3`} className="pt-cell pt-cell--empty" />)
    return cells
  }

  function handleBackdrop(e) {
    if (e.target === e.currentTarget) onClose()
  }

  return createPortal(
    <div className="pt-backdrop" onClick={handleBackdrop}>
      <div className="pt-panel">

        {/* ── Header ── */}
        <div className="pt-header">
          <div className="pt-header-left">
            <span className="pt-atom-icon">⚛</span>
            <span className="pt-title">Periodic Table of Elements</span>
          </div>
          <button className="pt-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        {/* ── Tab bar ── */}
        <div className="pt-tabs" role="tablist">
          {/* Static tabs */}
          {TABS.map(tab => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              className={`pt-tab${activeTab === tab.id ? ' pt-tab--active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}

          {/* Separator + element tabs */}
          {elementTabs.length > 0 && <span className="pt-tabs-sep" />}
          {elementTabs.map(el => {
            const [n, sym, , cat] = el
            const color = CAT_COLORS[cat] ?? CAT_COLORS.unknown
            const tabId = `el-${n}`
            const isActive = activeTab === tabId
            return (
              <div key={n} className={`pt-tab-el-wrap${isActive ? ' pt-tab-el-wrap--active' : ''}`}>
                <button
                  role="tab"
                  aria-selected={isActive}
                  className={`pt-tab pt-tab--el${isActive ? ' pt-tab--active' : ''}`}
                  style={{ '--el-color': color }}
                  onClick={() => setActiveTab(tabId)}
                >
                  {sym}
                </button>
                <button
                  className="pt-tab-el-close"
                  onClick={e => { e.stopPropagation(); closeElementTab(n) }}
                  aria-label={`Close ${sym}`}
                >×</button>
              </div>
            )
          })}
        </div>

        {/* ── Filter / toolbar zone (reserved for future controls) ── */}
        <div className="pt-toolbar">
          {/* filters and controls will live here */}
        </div>

        {/* ── Tab content ── */}
        {activeTab === 'table' && (
          <div className="pt-tab-content">

            {/* Main grid (periods 1–7) */}
            <div className="pt-grid">
              {mainCells}
            </div>

            {/* F-block separator */}
            <div className="pt-fblock-sep" />

            {/* Lanthanides */}
            <div className="pt-fblock-label" style={{ color: CAT_COLORS.lanthanide }}>
              Lanthanides
            </div>
            <div className="pt-grid pt-grid--fblock">
              {buildFRow(9)}
            </div>

            {/* Actinides */}
            <div className="pt-fblock-label" style={{ color: CAT_COLORS.actinide }}>
              Actinides
            </div>
            <div className="pt-grid pt-grid--fblock">
              {buildFRow(10)}
            </div>

            {/* Legend */}
            <div className="pt-legend">
              {Object.entries(CAT_LABELS).map(([cat, label]) => (
                <div key={cat} className="pt-legend-item">
                  <span className="pt-legend-dot" style={{ background: CAT_COLORS[cat] }} />
                  <span className="pt-legend-label">{label}</span>
                </div>
              ))}
            </div>

          </div>
        )}

        {/* By Category tab */}
        {activeTab === 'category' && (
          activeCategoryId
            ? <CategoryDetail
                categoryId={activeCategoryId}
                onBack={() => setActiveCategoryId(null)}
                onOpenElement={el => { openElementTab(el) }}
              />
            : <CategoryList onSelect={id => setActiveCategoryId(id)} />
        )}

        {/* Static tab placeholders for unbuilt tabs */}
        {activeTab !== 'table' && activeTab !== 'category' && !activeTab.startsWith('el-') && (
          <div className="pt-tab-placeholder">
            <span className="pt-tab-placeholder-icon">⚗</span>
            <span className="pt-tab-placeholder-text">
              {TABS.find(t => t.id === activeTab)?.label} — coming soon
            </span>
          </div>
        )}

        {/* Element profile */}
        {activeTab.startsWith('el-') && (() => {
          const n = parseInt(activeTab.slice(3))
          const el = elementTabs.find(e => e[0] === n)
          return el ? <ElementProfile el={el} /> : null
        })()}

      </div>
    </div>,
    document.body
  )
}
