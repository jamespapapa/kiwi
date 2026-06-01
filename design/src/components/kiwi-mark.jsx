/* global React */
const { useState } = React;

function KiwiMark({ size = 'md', className = '' }) {
  return (
    <span className={`kk-mark kk-mark-${size} ${className}`.trim()}>
      <img src="assets/kiwi.svg" alt="kiwi knows" />
    </span>
  );
}

function Icon({ name, size = 14 }) {
  const props = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 2,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
  };
  switch (name) {
    case 'arrow-right':  return <svg {...props}><path d="M5 12h14M13 5l7 7-7 7"/></svg>;
    case 'arrow-up-right': return <svg {...props}><path d="M7 17 17 7M9 7h8v8"/></svg>;
    case 'plus':         return <svg {...props}><path d="M12 5v14M5 12h14"/></svg>;
    case 'search':       return <svg {...props}><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>;
    case 'refresh':      return <svg {...props}><path d="M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5M21 12a9 9 0 0 1-15 6.7L3 16M3 21v-5h5"/></svg>;
    case 'copy':         return <svg {...props}><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>;
    case 'thumb-up':     return <svg {...props}><path d="M14 9V5a3 3 0 0 0-6 0v4H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12.5a2 2 0 0 0 2-1.5l1.5-7a2 2 0 0 0-2-2.5H14Z"/></svg>;
    case 'thumb-down':   return <svg {...props} style={{transform:'rotate(180deg)'}}><path d="M14 9V5a3 3 0 0 0-6 0v4H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12.5a2 2 0 0 0 2-1.5l1.5-7a2 2 0 0 0-2-2.5H14Z"/></svg>;
    case 'clock':        return <svg {...props}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>;
    case 'database':     return <svg {...props}><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v6c0 1.7 4 3 9 3s9-1.3 9-3V5M3 11v6c0 1.7 4 3 9 3s9-1.3 9-3v-6"/></svg>;
    case 'doc':          return <svg {...props}><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6Z"/><path d="M14 3v6h6M8 13h8M8 17h5"/></svg>;
    case 'git':          return <svg {...props}><circle cx="6" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="12" r="2"/><path d="M6 8v8M8 6h7a3 3 0 0 1 3 3v1"/></svg>;
    case 'pulse':        return <svg {...props}><path d="M3 12h4l3-9 4 18 3-9h4"/></svg>;
    case 'spark':        return <svg {...props}><path d="m12 3 2 7 7 2-7 2-2 7-2-7-7-2 7-2 2-7Z"/></svg>;
    case 'send':         return <svg {...props}><path d="M5 12h14M13 5l7 7-7 7"/></svg>;
    case 'check':        return <svg {...props}><path d="M5 12l5 5L20 7"/></svg>;
    case 'x':            return <svg {...props}><path d="M6 6l12 12M18 6 6 18"/></svg>;
    case 'eye':          return <svg {...props}><path d="M2 12s4-8 10-8 10 8 10 8-4 8-10 8S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>;
    case 'lock':         return <svg {...props}><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>;
    case 'mail':         return <svg {...props}><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>;
    default: return null;
  }
}

window.KiwiMark = KiwiMark;
window.Icon = Icon;
