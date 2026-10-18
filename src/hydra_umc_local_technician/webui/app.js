// =============================================================================
// HYDRA-UMC-LOCAL-TECHNICIAN - webui/app.js
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
// =============================================================================
// A read-only page: it only ever issues GET requests to this same origin, takes
// its strings from /i18n/<language>.json, and writes with textContent only.
(function () {
  "use strict";

  var LANGS = ["en", "es", "de", "fr", "it", "ja", "zh", "pt"];
  var FALLBACK = "en";
  var strings = {};
  var fallbackStrings = {};
  var current = null;      // view name
  var items = [];
  var selected = -1;
  var total = 0;
  var token = "";

  var $ = function (id) { return document.getElementById(id); };
  var enc = encodeURIComponent;

  function t(key, vars) {
    var text = strings[key];
    if (text === undefined) { text = fallbackStrings[key]; }
    if (text === undefined) { text = key; }
    if (vars) {
      Object.keys(vars).forEach(function (name) { text = text.split("{" + name + "}").join(String(vars[name])); });
    }
    return text;
  }

  function storageGet(key) { try { return window.localStorage.getItem(key); } catch (e) { return null; } }
  function storageSet(key, value) { try { window.localStorage.setItem(key, value); } catch (e) { /* storage may be blocked */ } }

  function pickLanguage() {
    var saved = storageGet("technician.lang");
    if (saved && LANGS.indexOf(saved) >= 0) { return saved; }
    var wanted = (navigator.language || FALLBACK).toLowerCase().split("-")[0];
    return LANGS.indexOf(wanted) >= 0 ? wanted : FALLBACK;
  }

  function loadStrings(lang) {
    return fetch("/i18n/" + lang + ".json", { method: "GET", cache: "no-store" }).then(function (r) {
      if (!r.ok) { throw new Error("i18n"); }
      return r.json();
    });
  }

  function applyStrings() {
    document.documentElement.lang = current_lang === "pt" ? "pt-PT" : current_lang;
    document.title = t("title");
    Array.prototype.forEach.call(document.querySelectorAll("[data-i18n]"), function (el) { el.textContent = t(el.getAttribute("data-i18n")); });
    Array.prototype.forEach.call(document.querySelectorAll("[data-i18n-placeholder]"), function (el) { el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder"))); });
    $("nav").setAttribute("aria-label", t("nav_label"));
    renderNav();
    if (current) { renderList(); renderDetailPlaceholder(); }
  }
  var current_lang = FALLBACK;

  function setLanguage(lang) {
    current_lang = lang;
    storageSet("technician.lang", lang);
    $("lang").value = lang;
    return loadStrings(lang).then(function (data) { strings = data; }).catch(function () { strings = {}; }).then(applyStrings);
  }

  // ---- views ---------------------------------------------------------------
  function storeView(name) {
    return {
      path: "/api/v1/" + name,
      paged: true,
      pick: function (r) { return r.items; },
      title: function (i) { return i.id; },
      meta: function (i) { return [i.status || i.risk || i.date || "", i.timestamp || i.scope || i.impact || ""].filter(Boolean).join(" · "); },
      detailPath: function (i) { return "/api/v1/" + name + "/" + enc(i.id); },
      show: function (r) { return r.item; }
    };
  }
  var VIEWS = {
    "tools": {
      path: "/api/v1/tools",
      pick: function (r) { return r.tools; },
      title: function (i) { return i.name; },
      meta: function (i) { return i.risk + " · " + t(i.implemented ? "implemented_yes" : "implemented_no"); },
      show: function (r) { return r; }
    },
    "tool-results": storeView("tool-results"),
    "evidence": storeView("evidence"),
    "proposals": storeView("proposals"),
    "manifests": {
      path: "/api/v1/manifests",
      pick: function (r) { return r.projects; },
      title: function (i) { return i.project; },
      meta: function (i) { return [i.version, i.maturity, i.role].filter(Boolean).join(" · "); },
      detailPath: function (i) { return "/api/v1/manifests/" + enc(i.project); },
      show: function (r) { return r; }
    },
    "docs": {
      path: "/api/v1/docs",
      pick: function (r) {
        var out = [];
        r.sources.forEach(function (s) { s.documents.forEach(function (d) { out.push({ source: s.name, path: d }); }); });
        return out;
      },
      title: function (i) { return i.path; },
      meta: function (i) { return i.source; },
      detailPath: function (i) { return "/api/v1/docs/" + enc(i.source) + "?path=" + enc(i.path); },
      docs: true
    }
  };
  var ORDER = ["tools", "tool-results", "evidence", "proposals", "manifests", "docs"];

  function renderNav() {
    var nav = $("nav");
    nav.textContent = "";
    ORDER.forEach(function (name) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = t("nav_" + name);
      if (name === current) { b.setAttribute("aria-current", "page"); }
      b.addEventListener("click", function () { openView(name); });
      nav.appendChild(b);
    });
  }

  function say(text, isError) {
    var el = $("status");
    el.textContent = text || "";
    el.className = isError ? "status error" : "status";
  }

  function api(path) {
    var headers = {};
    if (token) { headers["Authorization"] = "Bearer " + token; }
    return fetch(path, { method: "GET", headers: headers, cache: "no-store" }).then(function (r) {
      if (r.ok) { return r.json(); }
      var key = r.status === 401 ? "err_auth" : r.status === 413 ? "err_too_large" : r.status === 422 ? "err_invalid" : r.status === 404 ? "err_not_found" : "err_generic";
      var e = new Error(key);
      e.key = key;
      throw e;
    });
  }

  function failure(e) {
    say(t(e && e.key ? e.key : "err_network"), true);
  }

  function openView(name) {
    current = name;
    items = [];
    selected = -1;
    total = 0;
    renderNav();
    renderList();
    renderDetailPlaceholder();
    loadPage(0);
  }

  function loadPage(offset) {
    var view = VIEWS[current];
    var requested = current;
    say(t("loading"));
    var path = view.path + (view.paged ? "?offset=" + offset : "");
    api(path).then(function (data) {
      if (requested !== current) { return; }
      var page = view.pick(data) || [];
      items = items.concat(page);
      total = view.paged ? (data.total || items.length) : items.length;
      renderList();
      say(items.length === 0 ? t("empty") : t("count", { shown: items.length, total: total }));
    }).catch(failure);
  }

  function renderList() {
    var view = VIEWS[current];
    var ul = $("list");
    ul.textContent = "";
    if (!view) { return; }
    items.forEach(function (item, index) {
      var li = document.createElement("li");
      var b = document.createElement("button");
      b.type = "button";
      var title = document.createElement("span");
      title.className = "t";
      title.textContent = view.title(item);
      var meta = document.createElement("span");
      meta.className = "m";
      meta.textContent = view.meta(item);
      b.appendChild(title);
      b.appendChild(meta);
      if (index === selected) { b.setAttribute("aria-current", "true"); }
      b.addEventListener("click", function () { select(index); });
      li.appendChild(b);
      ul.appendChild(li);
    });
    $("more").hidden = !(view.paged && items.length < total);
  }

  function renderDetailPlaceholder() {
    var d = $("detail");
    d.textContent = "";
    var p = document.createElement("p");
    p.textContent = t("select_item");
    d.appendChild(p);
  }

  function showJson(value) {
    var d = $("detail");
    d.textContent = "";
    var pre = document.createElement("pre");
    pre.textContent = JSON.stringify(value, null, 2);
    d.appendChild(pre);
  }

  function showDocs(data) {
    var d = $("detail");
    d.textContent = "";
    data.chunks.forEach(function (chunk) {
      if (chunk.heading) {
        var h = document.createElement("h3");
        h.textContent = chunk.heading;
        d.appendChild(h);
      }
      var pre = document.createElement("pre");
      pre.textContent = chunk.text;
      d.appendChild(pre);
    });
    if (data.truncated) {
      var p = document.createElement("p");
      p.textContent = t("truncated");
      d.appendChild(p);
    }
  }

  function select(index) {
    var view = VIEWS[current];
    selected = index;
    renderList();
    var item = items[index];
    if (!view.detailPath) { showJson(item); return; }
    say(t("loading"));
    api(view.detailPath(item)).then(function (data) {
      if (view.docs) { showDocs(data); } else { showJson(view.show(data)); }
      say(t("count", { shown: items.length, total: total }));
      $("detail").focus();
    }).catch(failure);
  }

  // ---- start ---------------------------------------------------------------
  $("lang").addEventListener("change", function (e) { setLanguage(e.target.value); });
  $("token").addEventListener("change", function (e) { token = e.target.value.trim(); if (current) { openView(current); } });
  $("more").addEventListener("click", function () { loadPage(items.length); });

  loadStrings(FALLBACK).then(function (data) { fallbackStrings = data; }).catch(function () { fallbackStrings = {}; }).then(function () {
    return setLanguage(pickLanguage());
  }).then(function () { openView("tools"); });
})();
