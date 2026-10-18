/*!
 * resume-viewer.js
 * Embedded, lazy-loaded Syncfusion PDF Viewer for the résumé <dialog>.
 *
 * Markup contract (all URLs relative to the page):
 *   [data-resume-open]                 any number of buttons/links that open the viewer
 *   <dialog id="resume-dialog"
 *           data-pdf-url data-preview-url data-license-url
 *           data-css-url>              optional; defaults to ../css/resume-viewer.css
 *                                      relative to this script
 *     [data-resume-close]              closes the dialog
 *     <div id="resume-viewer">         the viewer fills this box (needs a definite height)
 *
 * Nothing Syncfusion-related loads until the dialog is opened for the first time.
 * With no license key (or a CDN failure, timeout, missing WebAssembly, or a document
 * that fails to load) it falls back to the page-one preview image plus a download link.
 *
 * Classic script, no build step. The only global it adds is window.ResumeViewer.
 */
(function () {
  "use strict";

  // The Syncfusion Community license key is valid for major version 34 only.
  // Do not move to v35+. If the version changes, regenerate every integrity hash:
  //   curl -s --compressed <url> | openssl dgst -sha384 -binary | openssl base64 -A
  var SF_VERSION = "34.2.9";
  var SF_CDN = "https://cdn.syncfusion.com/ej2/" + SF_VERSION + "/";
  var SF_RESOURCE_URL = SF_CDN + "dist/ej2-pdfviewer-lib";

  // Global (UMD) bundles in execution order: [package, ej.* namespace, sha384].
  // Smallest set that runs the view-only configuration below without errors.
  // Left out on purpose: ej2-pdf-data-extract (redaction only, 1.8 MB) and
  // ej2-inplace-editor with its chain (calendars, richtexteditor, filemanager, grids,
  // layouts, pdf-export, excel-export, interactive-chat, markdown-converter), which only
  // the annotation comment panel uses. Both features are disabled.
  var SF_SCRIPTS = [
    ["ej2-base", "base", "sha384-SxaFlCX+U3GM26303B8ENSYnhxEj7E5cO4V88bTIgJsKNdcl8jJ0Hn4FM37EPv1l"],
    ["ej2-data", "data", "sha384-4U4NFfQHh6Wp2d5k5ZH1g87dCv8MhGIp3H0/LIY085YPzJ9fQm4pWeFkaXwyHIKv"],
    ["ej2-buttons", "buttons", "sha384-rGP+biWP+QaAaheGa2q2ebtSawhQl8E2Ufe5zT21tsUpePqVnFfFd1WZK5LCA+PW"],
    ["ej2-popups", "popups", "sha384-pER6sWHa6e1lb/FcmY3R4F8L5PJFUWt7FQ2OJtCKAzR1UKZh/zs9odJjJ4jsjMIN"],
    ["ej2-lists", "lists", "sha384-8dH8xMe9dNwTVTgyzOA3EuEl7JU8Wi6vAzV/N+8wHfpqfc/FiYUSpGDRRq1GhzTi"],
    ["ej2-splitbuttons", "splitbuttons", "sha384-upx9FlaadbcRlsku8VLqAO5h5sWbogeUY68OjYjWu3UYTHUOKrp0lLxxPJqq2Eli"],
    ["ej2-inputs", "inputs", "sha384-CxYgF8jTkRth6RsJML6KfPQodOgcMr8WVZzPKQQTqiQea+8Xat2IN6GctfHg/OFq"],
    ["ej2-notifications", "notifications", "sha384-j1Xw78RdhtnSJ7jxfMwCVzGfSFtOP78cvf4RBQbZmrjFCsA3Rmw/C1kUDVWSLA/p"],
    ["ej2-navigations", "navigations", "sha384-ibP/x2ikUjB3B7kXjECS9HNyaxcCLYy0luVr4sLi/j2Cy3rvoLUR6FhP191KR36s"],
    ["ej2-dropdowns", "dropdowns", "sha384-uw2thgjs7g0rPolJQz9Nh780tN1gLqwav1LxJP4MUeSWRt7+v30ohVdtkUGvVYNu"],
    ["ej2-file-utils", "fileutils", "sha384-NTEqU8hyQEh5xhLXpdMzjEthamxi73ZJAmYpsV3v5O0EdZjxCC35NbZpfzcuv2g2"],
    ["ej2-compression", "compression", "sha384-SA7UiFf9khQzh6RkuohZjJ6k/KtsqCq/RkxyfJ/5BLELHw4mK3lGhPrxw740ijaS"],
    ["ej2-pdf", "pdf", "sha384-9Az4i9mYWingyZvWTOgXBFa+VvTDYc/ckqbmMD0apaux4l+Z3mRc9DKeiwcX1hGr"],
    ["ej2-pdfviewer", "pdfviewer", "sha384-HBg1GyISCItA4aOPL18qNMMldreAN/aMbTVcti9tnsYYUQAhBpJSF68M4fE8f9vU"]
  ];

  // material3-lite theme CSS for the packages the viewer actually renders: [package, sha384].
  var SF_STYLES = [
    ["ej2-base", "sha384-zuN3XYcFFlWKJf7LixaZhksKFmlzEAkzXyKHIILwCMd1U1DKTszMnGPA8TFrA8T7"],
    ["ej2-buttons", "sha384-sCz0A6X0PMt60nU5MjSwdhYYJYVlwUFYWv3PLR7jTjLT/psDLnkOfDc4CK8eP6Nw"],
    ["ej2-popups", "sha384-9XY2/0HsSL0UA1hgPXSfiR20vPkpoUU7RZ5/fg7SytYLTfqdO2foGnNiz1tpjDU8"],
    ["ej2-lists", "sha384-aPR/uZ+K2+WsMH7XVOqcF/FoQ7E5fkcEZ4oZMr/VGQf/b/Dw3OkwFFiCVS2Ch5oD"],
    ["ej2-splitbuttons", "sha384-cmkTat+++UaWg8C1Bwv1ADOZPFtWFq8Z6AYYwH695qk7R2f4KuX29nmpDnufQchH"],
    ["ej2-inputs", "sha384-3qrjEbXxBVS0AC87HVba7/A93cW8vDdISZwgutaYPQLRALv0pMDUdsI2ho/URK0m"],
    ["ej2-notifications", "sha384-tEU9f0FzNpMmQcD73MXNzgRcilhCrM9KwB21x283jcxhzkgoqWK53S9+/An3P/W0"],
    ["ej2-navigations", "sha384-Y0ue+nxS4AjuvFel+qcCgbHO6EKZg+RnRYaS97AjH8f+Wt8P1OgfY8wh016cvAsC"],
    ["ej2-dropdowns", "sha384-f0AGtmNlKHLw/U4j+8RIcr2JedLQ8INM4idBMvHmLzWikflckfHaWYH71O9+9b2A"],
    ["ej2-pdfviewer", "sha384-DCm/9j51eJ942Yb2VXgmeDfGtnlTPtCKZtAvRq8Jec3b9rwW/ibmnyYkjdH81GxI"]
  ];

  var LOAD_TIMEOUT_MS = 20000; // license + CSS + scripts
  var RENDER_TIMEOUT_MS = 20000; // WebAssembly start-up + first document load
  var DOWNLOAD_NAME = "Zach-Robida-Resume.pdf";
  var VIEWER_ID = "resume-viewer-pdf";
  var MAIL_LINK = /^(mailto|tel|sms):/i;

  // Syncfusion registers window/document input listeners (keyboard shortcuts, mouseup and
  // touchend handlers that touch the text selection, Safari pinch-zoom blockers, tooltip
  // key/scroll handlers). Those are detached whenever the dialog is closed.
  var PARKED_EVENTS = /^(key|mouse|pointer|touch|gesture|wheel|click|dblclick|auxclick|contextmenu|select|scroll)/;

  // Our stylesheet sits next to this script: assets/js/ -> assets/css/.
  var thisScript = document.currentScript;
  var STYLESHEET_URL = thisScript && thisScript.src
    ? resolveUrl("../css/resume-viewer.css", thisScript.src)
    : resolveUrl("assets/css/resume-viewer.css");

  var dialog;
  var host;
  var root;
  var statusEl;
  var opener = null;
  var state = "idle"; // idle -> loading -> ready | fallback
  var viewer = null;
  var listenerJail = null;
  var bannerObserver = null;
  var popupObserver = null;
  var linkObserver = null;
  var resizeObserver = null;
  var loadTimer = 0;
  var renderTimer = 0;
  var resolveWhenOpen = null;
  var backdropPointerDown = false;
  var openedAt = 0;
  var layoutWidth = -1;
  var layoutHeight = -1;

  function init() {
    dialog = document.getElementById("resume-dialog");
    host = document.getElementById("resume-viewer");
    if (!dialog || !host) {
      return;
    }

    document.addEventListener("click", onDocumentClick);
    dialog.addEventListener("click", onDialogClick);
    dialog.addEventListener("pointerdown", onDialogPointerDown);
    dialog.addEventListener("close", onDialogClose);

    window.ResumeViewer = {
      open: function () {
        openDialog(null);
      },
      close: closeDialog,
      get state() {
        return state;
      }
    };
  }

  // ---------------------------------------------------------------------------
  // Dialog behaviour

  function onDocumentClick(event) {
    var target = event.target;
    var trigger = target && target.closest ? target.closest("[data-resume-open]") : null;
    if (!trigger) {
      return;
    }
    // Let modified clicks on a link opener do their normal thing (new tab etc.).
    if (trigger.tagName === "A" && (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)) {
      return;
    }
    event.preventDefault();
    openDialog(trigger);
  }

  function onDialogClick(event) {
    var target = event.target;
    if (target && target.closest && target.closest("[data-resume-close]")) {
      event.preventDefault();
      closeDialog();
      return;
    }
    // Clicks on ::backdrop are dispatched to the <dialog> itself. Require the press to
    // start there too, so a text-selection drag released outside does not close it.
    if (target === dialog && backdropPointerDown && isOutsideDialog(event)) {
      closeDialog();
    }
    backdropPointerDown = false;
  }

  function onDialogPointerDown(event) {
    // Ignore presses right after opening: the second click of a double-click on the
    // opener lands on the backdrop.
    backdropPointerDown = event.target === dialog && isOutsideDialog(event) && Date.now() - openedAt > 500;
  }

  function isOutsideDialog(event) {
    var rect = dialog.getBoundingClientRect();
    return (
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    );
  }

  function openDialog(trigger) {
    opener = trigger || (document.activeElement !== document.body ? document.activeElement : null);
    if (!dialog.open) {
      openedAt = Date.now();
      if (typeof dialog.showModal === "function") {
        dialog.showModal();
      } else {
        dialog.setAttribute("open", "");
      }
    }
    setParked(false);

    if (state === "idle") {
      start();
    } else if (resolveWhenOpen) {
      var resume = resolveWhenOpen;
      resolveWhenOpen = null;
      resume();
    } else if (viewer) {
      refreshViewerLayout();
    }
  }

  // Syncfusion measures its box only at load and on window resize: not while the dialog is
  // hidden (closed mid-load, window resized while closed) and not when the dialog itself
  // changes size. Re-measure, and re-fit the page width unless the visitor has picked a
  // zoom level of their own.
  function refreshViewerLayout() {
    var width = root.clientWidth;
    var height = root.clientHeight;
    if (!viewer || !dialog.open || !width || (width === layoutWidth && height === layoutHeight)) {
      return;
    }
    var widthChanged = width !== layoutWidth;
    layoutWidth = width;
    layoutHeight = height;
    try {
      viewer.updateViewerContainer();
      var magnification = viewer.magnificationModule;
      if (widthChanged && magnification && magnification.fitType === "fitToWidth") {
        magnification.fitToWidth();
      }
    } catch (err) {
      // Layout refresh is best-effort.
    }
  }

  function closeDialog() {
    if (!dialog.open) {
      return;
    }
    if (typeof dialog.close === "function") {
      dialog.close();
    } else {
      dialog.removeAttribute("open");
      onDialogClose();
    }
  }

  function onDialogClose() {
    setParked(true);
    // Native <dialog> restores focus to the opener; make sure it did.
    var active = document.activeElement;
    if (opener && opener.isConnected && (!active || active === document.body || dialog.contains(active))) {
      try {
        opener.focus({ preventScroll: true });
      } catch (err) {
        opener.focus();
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Loading pipeline

  function start() {
    state = "loading";
    root = document.createElement("div");
    root.className = "resume-viewer";
    host.textContent = "";
    host.appendChild(root);
    host.setAttribute("aria-busy", "true");

    loadStylesheet(resolveUrl(dialog.getAttribute("data-css-url")) || STYLESHEET_URL);
    showStatus();

    var unsupported = getUnsupportedReason();
    if (unsupported) {
      fail(unsupported);
      return;
    }

    loadTimer = window.setTimeout(function () {
      fail("timed out loading the viewer");
    }, LOAD_TIMEOUT_MS);
    // Kept for the page's lifetime; they only act on errors thrown from Syncfusion code.
    window.addEventListener("error", onGlobalError);
    window.addEventListener("unhandledrejection", onGlobalRejection);

    var key;
    loadLicenseKey(resolveUrl(dialog.getAttribute("data-license-url")))
      .then(function (licenseKey) {
        key = licenseKey;
        return Promise.all([loadSyncfusionStyles(), loadSyncfusionScripts()]);
      })
      .then(function () {
        window.clearTimeout(loadTimer);
        // Never initialise inside a closed (display:none) dialog: wait for the next open.
        return whenDialogOpen();
      })
      .then(function () {
        if (state !== "loading") {
          return null;
        }
        renderTimer = window.setTimeout(function () {
          fail("timed out rendering the document");
        }, RENDER_TIMEOUT_MS);
        return createViewer(key);
      })
      .then(ready, function (err) {
        fail(err && err.message ? err.message : String(err));
      });
  }

  function getUnsupportedReason() {
    if (
      typeof Promise !== "function" ||
      typeof fetch !== "function" ||
      typeof Worker !== "function" ||
      typeof WebAssembly !== "object" ||
      typeof WebAssembly.instantiate !== "function"
    ) {
      return "WebAssembly, Worker, fetch or Promise is not available";
    }
    if (!dialog.getAttribute("data-pdf-url")) {
      return "data-pdf-url is missing";
    }
    return "";
  }

  function whenDialogOpen() {
    if (dialog.open) {
      return Promise.resolve();
    }
    return new Promise(function (resolve) {
      resolveWhenOpen = resolve;
    });
  }

  function loadLicenseKey(url) {
    return new Promise(function (resolve, reject) {
      if (!url) {
        reject(new Error("data-license-url is missing"));
        return;
      }
      var script = document.createElement("script");
      script.src = url;
      script.async = true;
      script.onload = function () {
        var licenseKey = window.SYNCFUSION_LICENSE_KEY;
        if (typeof licenseKey === "string" && licenseKey.trim()) {
          resolve(licenseKey.trim());
        } else {
          reject(new Error("no Syncfusion license key"));
        }
      };
      script.onerror = function () {
        reject(new Error("license script unavailable"));
      };
      document.head.appendChild(script);
    });
  }

  // Theme CSS is fetched (CORS + SRI) and inlined so the Roboto @import in ej2-base can
  // be dropped: the viewer uses the page font instead.
  function loadSyncfusionStyles() {
    return Promise.all(
      SF_STYLES.map(function (entry) {
        var url = SF_CDN + entry[0] + "/styles/material3-lite.css";
        return fetch(url, { mode: "cors", credentials: "omit", integrity: entry[1] }).then(
          function (res) {
            var type = res.headers.get("content-type") || "";
            if (!res.ok || type.indexOf("text/css") === -1) {
              throw new Error("could not load " + url);
            }
            return res.text();
          },
          function () {
            throw new Error("could not load " + url);
          }
        );
      })
    ).then(function (sheets) {
      var style = document.createElement("style");
      style.setAttribute("data-resume-viewer", "syncfusion");
      style.textContent = sheets.join("\n").replace(/@import\s+url\([^)]*fonts\.googleapis\.com[^)]*\)\s*;?/g, "");
      // Before our own stylesheet so its overrides win.
      var ours = document.querySelector('link[data-resume-viewer="theme"]');
      document.head.insertBefore(style, ours || null);
    });
  }

  // Downloads run in parallel; async=false keeps execution in dependency order.
  function loadSyncfusionScripts() {
    // The v34 pdfviewer global bundle reads a bare `ej2PdfDataExtract` global (used only for
    // redaction). Provide an empty stand-in until that bundle has run, then remove it.
    var stubbed = !("ej2PdfDataExtract" in window);
    if (stubbed) {
      window.ej2PdfDataExtract = {};
    }
    function removeStub() {
      if (stubbed) {
        stubbed = false;
        try {
          delete window.ej2PdfDataExtract;
        } catch (err) {
          window.ej2PdfDataExtract = undefined;
        }
      }
    }

    return new Promise(function (resolve, reject) {
      var pending = SF_SCRIPTS.length;
      var settled = false;
      function settle(err) {
        if (!settled) {
          settled = true;
          if (err) {
            reject(err);
          } else {
            resolve();
          }
        }
      }

      SF_SCRIPTS.forEach(function (entry, index) {
        var url = SF_CDN + entry[0] + "/dist/global/" + entry[0] + ".min.js";
        var isLast = index === SF_SCRIPTS.length - 1;
        var script = document.createElement("script");
        script.src = url;
        script.async = false;
        script.crossOrigin = "anonymous";
        script.integrity = entry[2];
        script.onload = function () {
          if (isLast) {
            removeStub();
          }
          if (!window.ej || !window.ej[entry[1]]) {
            settle(new Error(entry[0] + " did not initialise"));
          } else if (--pending === 0) {
            settle(null);
          }
        };
        script.onerror = function () {
          if (isLast) {
            removeStub();
          }
          settle(new Error("could not load " + url));
        };
        document.head.appendChild(script);
      });
    });
  }

  function createViewer(licenseKey) {
    var ej = window.ej;
    ej.base.registerLicense(licenseKey);
    if (prefersReducedMotion()) {
      ej.base.setGlobalAnimation("Disable");
    }
    keepPopupsInDialog(ej);

    // Syncfusion text uses var(--e-font-family); point it at the page's own font.
    var pageFont = window.getComputedStyle(host).fontFamily;
    if (pageFont) {
      root.style.setProperty("--e-font-family", pageFont);
    }

    var mount = document.createElement("div");
    mount.id = VIEWER_ID;
    mount.className = "resume-viewer__pdf";
    root.insertBefore(mount, statusEl || null);

    // Syncfusion's window keydown handler swallows Tab while the page canvas has focus
    // (form-field navigation that runs even with no form fields), trapping keyboard
    // users. Keep Tab native there.
    root.addEventListener("keydown", function (event) {
      if (event.key === "Tab" && event.target && event.target.id === VIEWER_ID + "_viewerContainer") {
        event.stopPropagation();
      }
    });

    installListenerJail();
    watchForLicenseBanner();
    watchMailLinks(mount);

    return new Promise(function (resolve, reject) {
      viewer = new ej.pdfviewer.PdfViewer({
        documentPath: resolveUrl(dialog.getAttribute("data-pdf-url")),
        resourceUrl: SF_RESOURCE_URL,
        downloadFileName: DOWNLOAD_NAME,
        height: "100%",
        width: "100%",
        zoomMode: "FitToWidth",
        enableToolbar: true,
        toolbarSettings: {
          showTooltip: true,
          toolbarItems: ["PageNavigationTool", "MagnificationTool", "SearchOption", "PrintOption", "DownloadOption"]
        },
        enableNavigationToolbar: false,
        enableThumbnail: false,
        enableBookmark: false,
        enableAnnotation: false,
        enableAnnotationToolbar: false,
        enableCommentPanel: false,
        enableFormFields: false,
        enableFormDesigner: false,
        enableFormDesignerToolbar: false,
        enableHandwrittenSignature: false,
        enablePageOrganizer: false,
        enableTextSelection: true,
        enableTextSearch: true,
        enableHyperlink: true,
        hyperlinkOpenState: "NewTab",
        enablePrint: true,
        enableDownload: true,
        contextMenuOption: "None",
        showNotificationDialog: false,
        hyperlinkClick: function (args) {
          // Open mail/phone links in place instead of through an empty new tab.
          if (MAIL_LINK.test(args.hyperlink || "")) {
            args.cancel = true;
            window.location.href = args.hyperlink;
          }
        },
        documentLoad: function () {
          resolve();
        },
        documentLoadFailed: function () {
          reject(new Error("the PDF failed to load"));
        }
      });

      viewer.appendTo(mount);

      // An unlicensed Syncfusion build announces itself with a banner on <body>.
      if (removeLicenseBanner()) {
        reject(new Error("Syncfusion rejected the license key"));
      }
    });
  }

  function ready() {
    if (state !== "loading") {
      return;
    }
    window.clearTimeout(renderTimer);
    if (removeLicenseBanner()) {
      fail("Syncfusion rejected the license key");
      return;
    }
    state = "ready";
    // The size the viewer was laid out at (-1 forces a refresh on the next open).
    layoutWidth = dialog.open ? root.clientWidth : -1;
    layoutHeight = dialog.open ? root.clientHeight : -1;
    host.removeAttribute("aria-busy");
    if (statusEl) {
      removeNode(statusEl);
      statusEl = null;
    }
    if (typeof ResizeObserver === "function") {
      resizeObserver = new ResizeObserver(refreshViewerLayout);
      resizeObserver.observe(root);
    }
  }

  // Switch to the fallback. Also reachable from "ready" if a license banner shows up late.
  function fail(reason) {
    if (state !== "loading" && state !== "ready") {
      return;
    }
    state = "fallback";
    window.clearTimeout(loadTimer);
    window.clearTimeout(renderTimer);
    if (bannerObserver) {
      bannerObserver.disconnect();
      bannerObserver = null;
    }
    if (popupObserver) {
      popupObserver.disconnect();
      popupObserver = null;
    }
    if (linkObserver) {
      linkObserver.disconnect();
      linkObserver = null;
    }
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    removeLicenseBanner();
    if (window.console && console.warn) {
      console.warn("[resume-viewer] Showing the fallback viewer: " + reason);
    }
    if (viewer) {
      try {
        viewer.destroy();
      } catch (err) {
        // Ignore: the fallback replaces the viewer markup anyway.
      }
      viewer = null;
    }
    uninstallListenerJail();
    renderFallback();
  }

  function onGlobalError(event) {
    var file = event.filename || "";
    var stack = (event.error && event.error.stack) || "";
    if (file.indexOf(SF_CDN) === 0 || stack.indexOf(SF_CDN) !== -1) {
      handleSyncfusionError(event, event.message);
    }
  }

  function onGlobalRejection(event) {
    var reason = event.reason;
    var stack = (reason && reason.stack) || "";
    if (stack.indexOf(SF_CDN) !== -1) {
      handleSyncfusionError(event, reason.message);
    }
  }

  // While loading, a Syncfusion error means fall back. After falling back, errors from the
  // abandoned instance (e.g. the rejected fetch behind documentLoadFailed) are swallowed.
  // Once the viewer is ready, errors surface normally.
  function handleSyncfusionError(event, message) {
    if (state === "loading") {
      event.preventDefault();
      fail("Syncfusion error: " + (message || "unknown"));
    } else if (state === "fallback") {
      event.preventDefault();
    }
  }

  function watchForLicenseBanner() {
    if (bannerObserver || typeof MutationObserver !== "function") {
      return;
    }
    bannerObserver = new MutationObserver(function () {
      if (removeLicenseBanner()) {
        fail("Syncfusion rejected the license key");
      }
    });
    bannerObserver.observe(document.body, { childList: true });
  }

  // ---------------------------------------------------------------------------
  // Loading state and fallback UI

  function showStatus() {
    statusEl = document.createElement("div");
    statusEl.className = "resume-viewer__status";

    var previewUrl = resolveUrl(dialog.getAttribute("data-preview-url"));
    if (previewUrl) {
      var preview = document.createElement("img");
      preview.className = "resume-viewer__status-preview";
      preview.alt = "";
      preview.decoding = "async";
      preview.onerror = function () {
        removeNode(preview);
      };
      preview.src = previewUrl;
      statusEl.appendChild(preview);
    }

    var message = document.createElement("p");
    message.className = "resume-viewer__status-message";
    message.setAttribute("role", "status");
    var spinner = document.createElement("span");
    spinner.className = "resume-viewer__spinner";
    spinner.setAttribute("aria-hidden", "true");
    message.appendChild(spinner);
    message.appendChild(document.createTextNode("Loading résumé…"));
    statusEl.appendChild(message);

    root.appendChild(statusEl);
  }

  function renderFallback() {
    var pdfUrl = resolveUrl(dialog.getAttribute("data-pdf-url"));
    var previewUrl = resolveUrl(dialog.getAttribute("data-preview-url"));

    root.textContent = "";
    statusEl = null;
    host.removeAttribute("aria-busy");

    // Page-one preview plus a download link. No <iframe> of the PDF: in-app browsers
    // (LinkedIn, Electron webviews) report navigator.pdfViewerEnabled yet render a blank frame.
    var wrap = document.createElement("div");
    wrap.className = "resume-viewer__fallback";

    var page = document.createElement("div");
    page.className = "resume-viewer__fallback-page";
    var showEmpty = function () {
      page.textContent = "The résumé preview isn’t available here. Download the PDF instead.";
      wrap.classList.add("is-empty");
    };
    if (previewUrl) {
      var img = document.createElement("img");
      img.className = "resume-viewer__fallback-image";
      img.alt = "Résumé, page 1";
      img.decoding = "async";
      img.style.cssText = "display:block;width:100%;height:auto;";
      img.onerror = showEmpty;
      img.src = previewUrl;
      page.appendChild(img);
    } else {
      showEmpty();
    }
    wrap.appendChild(page);

    if (pdfUrl) {
      var link = document.createElement("a");
      link.className = "resume-viewer__fallback-download";
      link.href = pdfUrl;
      link.setAttribute("download", DOWNLOAD_NAME);
      link.textContent = "Download PDF";
      wrap.appendChild(link);
    }

    root.appendChild(wrap);
  }

  // ---------------------------------------------------------------------------
  // Syncfusion integration helpers

  // A modal <dialog> sits in the browser's top layer, so popups that Syncfusion appends to
  // <body> would render underneath it and be inert. Re-home the viewer's popups into the
  // viewer root (position: relative, which Syncfusion's popup positioning accounts for).
  function keepPopupsInDialog(ej) {
    // The zoom list is created and positioned in one go, so redirect it at creation.
    var dropDown = ej.dropdowns && ej.dropdowns.DropDownList && ej.dropdowns.DropDownList.prototype;
    if (dropDown && typeof dropDown.getAppendToElement === "function") {
      var getAppendTo = dropDown.getAppendToElement;
      dropDown.getAppendToElement = function () {
        if (root && this.element && root.contains(this.element)) {
          return root;
        }
        return getAppendTo.apply(this, arguments);
      };
    }

    // Toolbar tooltips (their ids carry no viewer prefix).
    var tooltip = ej.popups && ej.popups.Tooltip && ej.popups.Tooltip.prototype;
    if (tooltip && typeof tooltip.appendContainer === "function") {
      var appendContainer = tooltip.appendContainer;
      tooltip.appendContainer = function () {
        if (root && this.container === "body" && this.element && root.contains(this.element)) {
          this.container = root;
        }
        return appendContainer.apply(this, arguments);
      };
    }

    // Everything else the viewer appends to <body> (the mobile "more options" menu, context
    // menus) is created up front, so moving it before it opens is enough. An already-open
    // popup is re-positioned after the move.
    if (!popupObserver && typeof MutationObserver === "function") {
      popupObserver = new MutationObserver(function (records) {
        records.forEach(function (record) {
          Array.prototype.forEach.call(record.addedNodes, rehomePopup);
        });
      });
      popupObserver.observe(document.body, { childList: true });
    }
  }

  // Syncfusion prefixes "http://" to any link URI without "http" in it, so the PDF's
  // mailto:/tel: links render as http://mailto:... (wrong on hover and "copy link").
  // The original URI is kept in the title; restore it for these schemes only.
  function watchMailLinks(mount) {
    if (linkObserver || typeof MutationObserver !== "function") {
      return;
    }
    linkObserver = new MutationObserver(function (records) {
      records.forEach(function (record) {
        Array.prototype.forEach.call(record.addedNodes, function (node) {
          var uri = node.tagName === "A" ? node.title || "" : "";
          if (MAIL_LINK.test(uri) && node.getAttribute("href") !== uri) {
            node.setAttribute("href", uri);
          }
        });
      });
    });
    linkObserver.observe(mount, { childList: true, subtree: true });
  }

  function rehomePopup(node) {
    if (!root || node.nodeType !== 1 || node.parentNode !== document.body) {
      return;
    }
    var owned =
      (node.id && node.id.indexOf(VIEWER_ID) === 0) ||
      (node.querySelector && node.querySelector('[id^="' + VIEWER_ID + '"]'));
    if (!owned) {
      return;
    }
    root.appendChild(node);
    var instance = node.ej2_instances && node.ej2_instances[0];
    if (instance && typeof instance.refreshPosition === "function" && node.classList.contains("e-popup-open")) {
      instance.refreshPosition();
    }
  }

  // While the viewer exists, keep a registry of the window/document input listeners that
  // Syncfusion code registers (identified by the CDN URL in the call stack; Syncfusion
  // wires several of them asynchronously), so they can be detached while the dialog is
  // closed. Listeners from any other code pass straight through.
  function installListenerJail() {
    if (listenerJail) {
      return;
    }
    var jail = { parked: !dialog.open, entries: [], targets: [] };
    listenerJail = jail;

    [window, document].forEach(function (target) {
      var saved = {
        target: target,
        add: target.addEventListener,
        remove: target.removeEventListener,
        ownAdd: Object.prototype.hasOwnProperty.call(target, "addEventListener"),
        ownRemove: Object.prototype.hasOwnProperty.call(target, "removeEventListener")
      };
      jail.targets.push(saved);

      target.addEventListener = function (type, listener, options) {
        if (listener && PARKED_EVENTS.test(type) && !isOneShot(options) && isSyncfusionCall()) {
          var capture = isCapture(options);
          if (findJailEntry(target, type, listener, capture) === -1) {
            jail.entries.push({ saved: saved, type: type, listener: listener, options: options, capture: capture });
          }
          if (jail.parked) {
            return undefined; // attached when the dialog opens
          }
        }
        return saved.add.call(this || target, type, listener, options);
      };

      target.removeEventListener = function (type, listener, options) {
        var index = findJailEntry(target, type, listener, isCapture(options));
        if (index !== -1) {
          jail.entries.splice(index, 1);
        }
        return saved.remove.call(this || target, type, listener, options);
      };
    });
  }

  function uninstallListenerJail() {
    if (!listenerJail) {
      return;
    }
    setParked(true);
    listenerJail.targets.forEach(function (saved) {
      if (saved.ownAdd) {
        saved.target.addEventListener = saved.add;
      } else {
        delete saved.target.addEventListener;
      }
      if (saved.ownRemove) {
        saved.target.removeEventListener = saved.remove;
      } else {
        delete saved.target.removeEventListener;
      }
    });
    listenerJail = null;
  }

  function setParked(parked) {
    var jail = listenerJail;
    if (!jail || jail.parked === parked) {
      return;
    }
    jail.parked = parked;
    jail.entries.forEach(function (entry) {
      var method = parked ? entry.saved.remove : entry.saved.add;
      method.call(entry.saved.target, entry.type, entry.listener, entry.options);
    });
  }

  function findJailEntry(target, type, listener, capture) {
    var entries = listenerJail ? listenerJail.entries : [];
    for (var i = 0; i < entries.length; i += 1) {
      var entry = entries[i];
      if (entry.saved.target === target && entry.type === type && entry.listener === listener && entry.capture === capture) {
        return i;
      }
    }
    return -1;
  }

  function isCapture(options) {
    return typeof options === "boolean" ? options : !!(options && options.capture);
  }

  function isOneShot(options) {
    return !!(options && typeof options === "object" && (options.once || options.signal));
  }

  function isSyncfusionCall() {
    var stack = new Error().stack || "";
    return stack.indexOf(SF_CDN) !== -1;
  }

  // Matches only Syncfusion's own banner markup (close button / "claim license" link).
  function removeLicenseBanner() {
    var found = false;
    var nodes = document.body.children;
    for (var i = nodes.length - 1; i >= 0; i -= 1) {
      var node = nodes[i];
      if (node.tagName === "DIV" && node.querySelector('.license-banner-close, a[href*="claim-license-key"]')) {
        removeNode(node);
        found = true;
      }
    }
    return found;
  }

  // ---------------------------------------------------------------------------
  // Small utilities

  function loadStylesheet(href) {
    if (document.querySelector('link[data-resume-viewer="theme"]')) {
      return;
    }
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.setAttribute("data-resume-viewer", "theme");
    document.head.appendChild(link);
  }

  function resolveUrl(value, base) {
    if (!value) {
      return "";
    }
    try {
      return new URL(value, base || document.baseURI).href;
    } catch (err) {
      return value;
    }
  }

  function prefersReducedMotion() {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function removeNode(node) {
    if (node && node.parentNode) {
      node.parentNode.removeChild(node);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
