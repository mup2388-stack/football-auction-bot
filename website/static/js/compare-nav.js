/**
 * Compare page — instant navigation (no full reload, no skeleton).
 *
 * Progressive enhancement: intercepts clicks on internal /compare links and
 * filter-form submits, fetches the new page, and swaps ONLY the
 * <section class="cmp"> block. Nav + footer + chrome stay put. On any error
 * it falls back to a normal full navigation.
 *
 * Skill basis (Emil): interactions a user fires dozens of times must feel
 * instant. Compare is exactly that (pick / remove / page), so there is no
 * animation on the swap — just a fast replace. Reduced-motion users get the
 * same instant swap (it's instant already).
 */
(function () {
  "use strict";

  var SECTION_SEL = "section.cmp";
  var running = false;

  function isCompareHref(href) {
    if (!href || href[0] === "#") return false;
    try {
      return new URL(href, window.location.href).pathname === "/compare";
    } catch (e) {
      return href.indexOf("/compare") === 0;
    }
  }

  function isCompareLink(el) {
    return el && el.tagName === "A" && isCompareHref(el.getAttribute("href"));
  }

  function swapSection(html) {
    var doc = new DOMParser().parseFromString(html, "text/html");
    var incoming = doc.querySelector(SECTION_SEL);
    var current = document.querySelector(SECTION_SEL);
    if (!incoming || !current) return false;
    current.replaceWith(incoming);
    return incoming; // return new node so we can bind to it
  }

  function bindSection(root) {
    // link clicks: slot picks, clear X, pagination, clear-filters
    root.addEventListener("click", function (e) {
      if (e.defaultPrevented || e.button !== 0) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      var a = e.target.closest("a");
      if (!isCompareLink(a)) return;
      e.preventDefault();
      go(a.href, true);
    });

    // filter form submit
    var form = root.querySelector("form.cmp-filters");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var qs = new URLSearchParams(new FormData(form)).toString();
        go("/compare?" + qs, true);
      });
    }
  }

  function go(url, push) {
    if (running) return;
    running = true;
    fetch(url, { headers: { "X-Compare-Nav": "1" }, credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("status " + r.status);
        return r.text();
      })
      .then(function (html) {
        var node = swapSection(html);
        if (!node) throw new Error("no compare section in response");
        if (push) window.history.pushState({ cmpNav: true }, "", url);
        bindSection(node); // rebind to the freshly swapped node
        // keep the selection rail in view so context isn't lost
        var rail = node.querySelector(".cmp-rail");
        if (rail) {
          var top = rail.getBoundingClientRect().top + window.scrollY - 80;
          window.scrollTo({ top: Math.max(0, top), behavior: "auto" });
        }
      })
      .catch(function () {
        window.location.href = url; // graceful full-nav fallback
      })
      .finally(function () { running = false; });
  }

  // back / forward — swap without pushing a new history entry
  window.addEventListener("popstate", function () {
    if (!document.querySelector(SECTION_SEL)) return;
    go(window.location.href, false);
  });

  function init() {
    var root = document.querySelector(SECTION_SEL);
    if (root) bindSection(root);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
