// One stroke family for every icon: 20px box, 1.75 stroke, round caps.
type Props = { className?: string }
const base = { width: 20, height: 20, viewBox: '0 0 20 20', fill: 'none', stroke: 'currentColor', strokeWidth: 1.75, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true }

export const Close = (p: Props) => <svg {...base} {...p}><path d="M5.5 5.5l9 9M14.5 5.5l-9 9" /></svg>
export const Chevron = (p: Props) => <svg {...base} {...p}><path d="M6 8l4 4 4-4" /></svg>
export const Upload = (p: Props) => <svg {...base} {...p}><path d="M10 13V3.5M6.5 7L10 3.5 13.5 7M4 12.5v3a1 1 0 001 1h10a1 1 0 001-1v-3" /></svg>
export const Send = (p: Props) => <svg {...base} {...p}><path d="M4 10h11M11 5.5l4.5 4.5L11 14.5" /></svg>
export const External = (p: Props) => <svg {...base} {...p}><path d="M11.5 4H16v4.5M16 4l-7 7M14 11.5V15a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h3.5" /></svg>
export const Alert = (p: Props) => <svg {...base} {...p}><path d="M10 3.5l7 12.5H3L10 3.5zM10 8.5v3M10 14h.01" /></svg>
export const Check = (p: Props) => <svg {...base} {...p}><path d="M4.5 10.5l3.5 3.5 7.5-8" /></svg>
export const Met = (p: Props) => <svg {...base} {...p}><circle cx="10" cy="10" r="7" /><path d="M7 10.2l2 2 4-4.4" /></svg>
export const Partial = (p: Props) => <svg {...base} {...p}><circle cx="10" cy="10" r="7" /><path d="M7 10h6" /></svg>
export const NotMet = (p: Props) => <svg {...base} {...p}><circle cx="10" cy="10" r="7" /><path d="M7.6 7.6l4.8 4.8M12.4 7.6l-4.8 4.8" /></svg>
export const Info = (p: Props) => <svg {...base} {...p}><circle cx="10" cy="10" r="7" /><path d="M10 9v4.5M10 6.5h.01" /></svg>
export const Question = (p: Props) => <svg {...base} {...p}><circle cx="10" cy="10" r="7" /><path d="M8.2 8.2a1.9 1.9 0 113 1.6c-.8.5-1.2.9-1.2 1.7M10 13.8h.01" /></svg>
