/**
 * Hex attribute wheel — PAC / SHO / PAS / DRI / DEF / PHY
 * Pure SVG, no chart libraries. One job: paint the wagon wheel.
 */
(function () {
  "use strict";

  // Clockwise from top-left (matches FIFA-ish layout in the ref shot)
  // PAC NW, SHO NE, PAS E, DRI SE, DEF SW, PHY W
  // For GKs the template passes data-axes="DIV,HAN,KIC,REF,SPD,POS" + the
  // matching data-div/data-han/... values, so the wheel shows real GK stats
  // under correct labels instead of mislabeling them as PAC/SHO/...
  var ANGLES = [-120, -60, 0, 60, 120, 180];
  var DEFAULT_KEYS = ["pac", "sho", "pas", "dri", "def", "phy"];
  var DEFAULT_LABELS = ["PAC", "SHO", "PAS", "DRI", "DEF", "PHY"];
  // Label colors — slight spice, not rainbow vomit
  var COLORS = ["#5B9BD5", "#70AD47", "#70AD47", "#70AD47", "#ED7D31", "#FFC000"];

  function deg2rad(d) {
    return (d * Math.PI) / 180;
  }

  function pt(cx, cy, r, angleDeg) {
    var a = deg2rad(angleDeg);
    return {
      x: cx + r * Math.cos(a),
      y: cy + r * Math.sin(a),
    };
  }

  function hexPoints(cx, cy, r) {
    var pts = [];
    for (var i = 0; i < 6; i++) {
      var p = pt(cx, cy, r, ANGLES[i]);
      pts.push(p.x.toFixed(2) + "," + p.y.toFixed(2));
    }
    return pts.join(" ");
  }

  function clampStat(n) {
    n = Number(n);
    if (!isFinite(n)) n = 40;
    if (n < 1) n = 1;
    if (n > 99) n = 99;
    return n;
  }

  function paint(stage) {
    var svg = stage.querySelector(".radar-svg");
    if (!svg) return;

    var rings = svg.querySelector(".radar-rings");
    var spokes = svg.querySelector(".radar-spokes");
    var shape = svg.querySelector(".radar-shape");
    var dots = svg.querySelector(".radar-dots");
    var labels = svg.querySelector(".radar-labels");
    if (!rings || !shape) return;

    rings.innerHTML = "";
    spokes.innerHTML = "";
    dots.innerHTML = "";
    labels.innerHTML = "";

    var cx = 160;
    var cy = 160;
    var maxR = 108;

    // Resolve axes: GK stages carry data-axes="DIV,HAN,..."; outfield stages
    // default to PAC/SHO/PAS/DRI/DEF/PHY. Keys are lowercased label names so
    // the wheel reads data-div, data-pac, etc. from the stage.
    var axesAttr = stage.getAttribute("data-axes");
    var KEYS, LABELS;
    if (axesAttr && axesAttr.trim()) {
      LABELS = axesAttr.split(",").map(function (s) { return s.trim(); });
      KEYS = LABELS.map(function (s) { return s.toLowerCase(); });
    } else {
      KEYS = DEFAULT_KEYS;
      LABELS = DEFAULT_LABELS;
    }

    // Concentric hex rings — translucent so it sits clean on the hero
    var ringFills = [
      "rgba(22, 78, 46, 0.55)",
      "rgba(30, 98, 54, 0.48)",
      "rgba(42, 118, 62, 0.40)",
      "rgba(58, 136, 70, 0.32)",
      "rgba(78, 154, 78, 0.24)",
    ];
    for (var i = 0; i < 5; i++) {
      var rr = maxR * (1 - i * 0.16);
      var poly = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
      poly.setAttribute("points", hexPoints(cx, cy, rr));
      poly.setAttribute("fill", ringFills[i]);
      poly.setAttribute("stroke", "rgba(180, 220, 190, 0.18)");
      poly.setAttribute("stroke-width", "1");
      rings.appendChild(poly);
    }

    // Spokes
    for (var s = 0; s < 6; s++) {
      var tip = pt(cx, cy, maxR, ANGLES[s]);
      var line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", cx);
      line.setAttribute("y1", cy);
      line.setAttribute("x2", tip.x);
      line.setAttribute("y2", tip.y);
      line.setAttribute("stroke", "rgba(200, 230, 210, 0.14)");
      line.setAttribute("stroke-width", "1");
      spokes.appendChild(line);
    }

    // Player shape
    var vals = KEYS.map(function (k) {
      return clampStat(stage.dataset[k]);
    });
    var shapePts = [];
    for (var j = 0; j < 6; j++) {
      var r = (vals[j] / 99) * maxR;
      var p = pt(cx, cy, r, ANGLES[j]);
      shapePts.push(p.x.toFixed(2) + "," + p.y.toFixed(2));

      var dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      dot.setAttribute("cx", p.x);
      dot.setAttribute("cy", p.y);
      dot.setAttribute("r", 4.2);
      dot.setAttribute("fill", "#F4FFF2");
      dot.setAttribute("stroke", "rgba(20, 60, 30, 0.85)");
      dot.setAttribute("stroke-width", "1.5");
      dots.appendChild(dot);
    }
    shape.setAttribute("points", shapePts.join(" "));

    // Labels outside the wheel
    var labelR = maxR + 28;
    for (var L = 0; L < 6; L++) {
      var lp = pt(cx, cy, labelR, ANGLES[L]);
      var g = document.createElementNS("http://www.w3.org/2000/svg", "g");

      var name = document.createElementNS("http://www.w3.org/2000/svg", "text");
      name.setAttribute("x", lp.x);
      name.setAttribute("y", lp.y - 6);
      name.setAttribute("text-anchor", "middle");
      name.setAttribute("dominant-baseline", "middle");
      name.setAttribute("fill", COLORS[L]);
      name.setAttribute("font-size", "13");
      name.setAttribute("font-weight", "800");
      name.setAttribute("font-family", "Inter, system-ui, sans-serif");
      name.setAttribute("letter-spacing", "0.04em");
      name.textContent = LABELS[L];

      var num = document.createElementNS("http://www.w3.org/2000/svg", "text");
      num.setAttribute("x", lp.x);
      num.setAttribute("y", lp.y + 12);
      num.setAttribute("text-anchor", "middle");
      num.setAttribute("dominant-baseline", "middle");
      num.setAttribute("fill", COLORS[L]);
      num.setAttribute("font-size", "15");
      num.setAttribute("font-weight", "800");
      num.setAttribute("font-family", "Inter, system-ui, sans-serif");
      num.textContent = String(vals[L]);

      g.appendChild(name);
      g.appendChild(num);
      labels.appendChild(g);
    }
  }

  function boot() {
    document.querySelectorAll(".radar-stage").forEach(paint);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
