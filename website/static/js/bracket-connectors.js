/* ===========================================================================
   BRACKET CONNECTORS — draws SVG lines between matches
   Left side flows RIGHTWARD, right side flows LEFTWARD, both → Final.
   =========================================================================== */

function drawBracketConnectors() {
  const tree = document.getElementById('bracket-tree');
  const svg = document.getElementById('bracket-svg');
  if (!tree || !svg) return;

  const treeRect = tree.getBoundingClientRect();

  svg.setAttribute('width', tree.scrollWidth);
  svg.setAttribute('height', tree.scrollHeight);
  svg.style.width = tree.scrollWidth + 'px';
  svg.style.height = tree.scrollHeight + 'px';
  svg.innerHTML = '';

  const NS = 'http://www.w3.org/2000/svg';
  const LINE = '#3A3A46';
  const GOLD = '#B89040';

  function drawPath(x1, y1, x2, y2, color) {
    const p = document.createElementNS(NS, 'path');
    const midX = (x1 + x2) / 2;
    p.setAttribute('d', `M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}`);
    p.setAttribute('stroke', color);
    p.setAttribute('stroke-width', '1.5');
    p.setAttribute('fill', 'none');
    svg.appendChild(p);
  }

  // Get edge of a match relative to tree
  function edge(el, useRight) {
    const r = el.getBoundingClientRect();
    const tr = tree.getBoundingClientRect();
    return {
      x: useRight ? (r.right - tr.left) : (r.left - tr.left),
      y: r.top - tr.top + r.height / 2,
    };
  }

  // LEFT SIDE: R16→QF→SF→Final, each column connects to the NEXT (toward center)
  function connectLeft(cols, finalCol) {
    cols.forEach((col, ci) => {
      const next = cols[ci + 1] || finalCol;
      if (!next) return;
      const matches = col.querySelectorAll('.bk-match');
      const parentMatches = next.querySelectorAll('.bk-match');
      const isToFinal = !cols[ci + 1];
      const color = isToFinal ? GOLD : LINE;

      for (let i = 0; i < matches.length; i += 2) {
        const m1 = matches[i];
        const m2 = matches[i + 1];
        const parentIdx = Math.floor(i / 2);
        const parent = parentMatches[parentIdx];
        if (!m1 || !parent) continue;

        const p1 = edge(m1, true);  // right edge of source
        const tp = edge(parent, false); // left edge of parent
        drawPath(p1.x, p1.y, tp.x, tp.y, color);

        if (m2) {
          const p2 = edge(m2, true);
          drawPath(p2.x, p2.y, tp.x, tp.y, color);
        }
      }
    });
  }

  // RIGHT SIDE: SF→QF→R16 in template order (reversed).
  // SF connects to Final, QF connects to SF, R16 connects to QF.
  // Each column connects to the PREVIOUS one (index i-1), toward center.
  function connectRight(cols, finalCol) {
    cols.forEach((col, ci) => {
      // SF (ci=0) → Final, QF (ci=1) → SF (cols[0]), R16 (ci=2) → QF (cols[1])
      const next = (ci === 0) ? finalCol : cols[ci - 1];
      if (!next) return;
      const matches = col.querySelectorAll('.bk-match');
      const parentMatches = next.querySelectorAll('.bk-match');
      const isToFinal = (ci === 0);
      const color = isToFinal ? GOLD : LINE;

      for (let i = 0; i < matches.length; i += 2) {
        const m1 = matches[i];
        const m2 = matches[i + 1];
        const parentIdx = Math.floor(i / 2);
        const parent = parentMatches[parentIdx];
        if (!m1 || !parent) continue;

        // Right side: source LEFT edge, parent RIGHT edge
        const p1 = edge(m1, false);  // left edge of source
        const tp = edge(parent, true);  // right edge of parent
        drawPath(p1.x, p1.y, tp.x, tp.y, color);

        if (m2) {
          const p2 = edge(m2, false);
          drawPath(p2.x, p2.y, tp.x, tp.y, color);
        }
      }
    });
  }

  const leftCols = Array.from(tree.querySelectorAll('.bk-left .bk-col-wrap'));
  const rightCols = Array.from(tree.querySelectorAll('.bk-right .bk-col-wrap'));
  const finalCol = tree.querySelector('.bk-final-col');

  connectLeft(leftCols, finalCol);
  connectRight(rightCols, finalCol);
}

window.addEventListener('load', () => {
  setTimeout(drawBracketConnectors, 200);
});

let rt;
window.addEventListener('resize', () => {
  clearTimeout(rt);
  rt = setTimeout(drawBracketConnectors, 200);
});
