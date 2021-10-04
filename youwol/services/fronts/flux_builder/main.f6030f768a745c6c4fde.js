/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ({

/***/ "./style.css":
/*!*******************!*\
  !*** ./style.css ***!
  \*******************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
// extracted by mini-css-extract-plugin


/***/ }),

/***/ "./loading.views.ts":
/*!**************************!*\
  !*** ./loading.views.ts ***!
  \**************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "loadingProjectView": () => (/* binding */ loadingProjectView),
/* harmony export */   "loadingLibView": () => (/* binding */ loadingLibView),
/* harmony export */   "loadingErrorView": () => (/* binding */ loadingErrorView),
/* harmony export */   "includeYouWolLogoView": () => (/* binding */ includeYouWolLogoView)
/* harmony export */ });
/* harmony import */ var _youwol_cdn_client__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/cdn-client */ "@youwol/cdn-client");
/* harmony import */ var _youwol_cdn_client__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_cdn_client__WEBPACK_IMPORTED_MODULE_0__);

function loadingProjectView(loadingDiv) {
    let divProjectLoading = document.createElement('div');
    divProjectLoading.style.setProperty("color", "lightgray");
    divProjectLoading.innerText = `> project loading...`;
    loadingDiv.appendChild(divProjectLoading);
    return divProjectLoading;
}
function loadingLibView(event, loadingDiv) {
    let libraryName = event.targetName;
    let cssId = libraryName.replace("/", "-").replace("@", "");
    let divLib = document.querySelector(`#${cssId}`);
    if (!divLib) {
        divLib = document.createElement('div');
        divLib.id = cssId;
        loadingDiv.appendChild(divLib);
    }
    if (event instanceof _youwol_cdn_client__WEBPACK_IMPORTED_MODULE_0__.StartEvent) {
        divLib.style.setProperty("color", "lightgray");
        divLib.innerText = `> ${libraryName} ... loading: 0 kB`;
    }
    if (event instanceof _youwol_cdn_client__WEBPACK_IMPORTED_MODULE_0__.SourceLoadingEvent) {
        divLib.style.setProperty("color", "lightgray");
        divLib.innerText = `> ${libraryName} ... loading: ${event.progress.loaded / 1000} kB`;
    }
    if (event instanceof _youwol_cdn_client__WEBPACK_IMPORTED_MODULE_0__.SourceLoadedEvent) {
        divLib.style.setProperty("color", "green");
        divLib.innerText = `> ${libraryName} ${event.progress.loaded / 1000} kB`;
    }
    if (event instanceof _youwol_cdn_client__WEBPACK_IMPORTED_MODULE_0__.UnauthorizedEvent) {
        divLib.style.setProperty("color", "red");
        divLib.style.setProperty("font-size", "small");
        divLib.innerText = `> ${libraryName} : You don't have permission to access this resource.`;
    }
}
function loadingErrorView(error, loadingDiv) {
    let divError = document.createElement('div');
    if (error instanceof _youwol_cdn_client__WEBPACK_IMPORTED_MODULE_0__.LoadingGraphError) {
        divError.style.setProperty("color", "red");
        loadingDiv.appendChild(divError);
        error.errorResponse.then(r => {
            divError.innerText = `x -> ${r.detail}\n`;
            if (r.parameters && r.parameters.packages) {
                divError.innerText += r.parameters.packages;
            }
            console.log(r);
        });
    }
}
function includeYouWolLogoView() {
    document.getElementById("youwol-logo-loading-screen").innerText = `
                *@@@@@@,         
                *@@@@@@,                
      /@@@@@@%  *@@@@@@,  %@@@@@@(      
    ,&@@@@@@@@@@@@@@@@@@@@@@@@@@@@&*    
         %@@@@@@@@@@@@@@@@@@@@%         
(            /@@@@@@@@@@@@/            /
@@@@#.           ,&@@&*           .#@@@@
@@@@@@@@@.                    .@@@@@@@@@
#@@@@@@@@@@@@(            (@@@@@@@@@@@@#
    /@@@@@@@@@@@#      #@@@@@@@@@@@(    
    *@@@@@@@@@@@#      #@@@@@@@@@@@/    
(@@@@@@@@@@@@@@@#      #@@@@@@@@@@@@@@@#
@@@@@@@@@*&@@@@@#      #@@@@@&,@@@@@@@@@
 .#@%.    &@@@@@#      #@@@@@&    .#@%. 
          &@@@@@#      #@@@@@&          
          ,@@@@@#      #@@@@@,          
              .##      ##.    
`;
}


/***/ }),

/***/ "./main.ts":
/*!*****************!*\
  !*** ./main.ts ***!
  \*****************/
/***/ ((module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.a(module, async (__webpack_handle_async_dependencies__) => {
__webpack_require__.r(__webpack_exports__);
/* harmony import */ var _loading_views__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./loading.views */ "./loading.views.ts");
// Following import is to include style.css in the dist directory (using MiniCssExtractPlugin)
__webpack_require__(/*! ./style.css */ "./style.css");

let cdn = window['@youwol/cdn-client'];
let loadingDiv = document.getElementById("content-loading-screen");
(0,_loading_views__WEBPACK_IMPORTED_MODULE_0__.includeYouWolLogoView)();
let stylesFutures = cdn.fetchStyleSheets([
    "bootstrap#4.4.1~bootstrap.min.css",
    "fontawesome#5.12.1~css/all.min.css",
    "@youwol/fv-widgets#0.0.3~dist/assets/styles/style.youwol.css",
    "grapes#0.17.26~css/grapes.min.css",
    "codemirror#5.52.0~codemirror.min.css",
    "codemirror#5.52.0~theme/blackboard.min.css",
]);
let bundlesFutures = cdn.fetchBundles({
    'lodash': '4.17.15',
    "grapes": '0.17.26',
    "@youwol/flux-core": 'latest',
    "@youwol/flux-svg-plots": 'latest',
    '@youwol/flux-view': 'latest',
    "@youwol/fv-group": "latest",
    "@youwol/fv-button": "latest",
    "@youwol/fv-tree": "latest",
    "@youwol/fv-tabs": "latest",
    "@youwol/fv-input": "latest",
    "@youwol/fv-context-menu": "latest",
    "rxjs": '6.5.5',
}, window, (event) => {
    (0,_loading_views__WEBPACK_IMPORTED_MODULE_0__.loadingLibView)(event, loadingDiv);
})
    .catch((error) => {
    (0,_loading_views__WEBPACK_IMPORTED_MODULE_0__.loadingErrorView)(error, loadingDiv);
});
let [styles] = await Promise.all([stylesFutures, bundlesFutures]);
let [linkBA, linfFA, linkYW, _] = styles;
linkBA.id = "bootstrap-css";
linkYW.id = "youwol-css";
linfFA.id = "fontawesome-css";
window['codemirror'] = {}; // code mirror will be fetched in due time (when opening the editor)
await Promise.all(/*! import() */[__webpack_require__.e("vendors-node_modules_d3-drag_src_drag_js-node_modules_tslib_tslib_es6_js"), __webpack_require__.e("on-load_ts")]).then(__webpack_require__.bind(__webpack_require__, /*! ./on-load */ "./on-load.ts"));

__webpack_handle_async_dependencies__();
}, 1);

/***/ }),

/***/ "@youwol/cdn-client":
/*!***********************************************!*\
  !*** external "window['@youwol/cdn-client']" ***!
  \***********************************************/
/***/ ((module) => {

module.exports = window['@youwol/cdn-client'];

/***/ }),

/***/ "@youwol/flux-core":
/*!**********************************************!*\
  !*** external "window['@youwol/flux-core']" ***!
  \**********************************************/
/***/ ((module) => {

module.exports = window['@youwol/flux-core'];

/***/ }),

/***/ "@youwol/flux-svg-plots":
/*!***************************************************!*\
  !*** external "window['@youwol/flux-svg-plots']" ***!
  \***************************************************/
/***/ ((module) => {

module.exports = window['@youwol/flux-svg-plots'];

/***/ }),

/***/ "@youwol/flux-view":
/*!**********************************************!*\
  !*** external "window['@youwol/flux-view']" ***!
  \**********************************************/
/***/ ((module) => {

module.exports = window['@youwol/flux-view'];

/***/ }),

/***/ "@youwol/fv-button":
/*!**********************************************!*\
  !*** external "window['@youwol/fv-button']" ***!
  \**********************************************/
/***/ ((module) => {

module.exports = window['@youwol/fv-button'];

/***/ }),

/***/ "@youwol/fv-context-menu":
/*!****************************************************!*\
  !*** external "window['@youwol/fv-context-menu']" ***!
  \****************************************************/
/***/ ((module) => {

module.exports = window['@youwol/fv-context-menu'];

/***/ }),

/***/ "@youwol/fv-group":
/*!*********************************************!*\
  !*** external "window['@youwol/fv-group']" ***!
  \*********************************************/
/***/ ((module) => {

module.exports = window['@youwol/fv-group'];

/***/ }),

/***/ "@youwol/fv-input":
/*!*********************************************!*\
  !*** external "window['@youwol/fv-input']" ***!
  \*********************************************/
/***/ ((module) => {

module.exports = window['@youwol/fv-input'];

/***/ }),

/***/ "@youwol/fv-tabs":
/*!********************************************!*\
  !*** external "window['@youwol/fv-tabs']" ***!
  \********************************************/
/***/ ((module) => {

module.exports = window['@youwol/fv-tabs'];

/***/ }),

/***/ "@youwol/fv-tree":
/*!********************************************!*\
  !*** external "window['@youwol/fv-tree']" ***!
  \********************************************/
/***/ ((module) => {

module.exports = window['@youwol/fv-tree'];

/***/ }),

/***/ "lodash":
/*!******************************!*\
  !*** external "window['_']" ***!
  \******************************/
/***/ ((module) => {

module.exports = window['_'];

/***/ }),

/***/ "grapesjs":
/*!*************************************!*\
  !*** external "window['grapesjs']" ***!
  \*************************************/
/***/ ((module) => {

module.exports = window['grapesjs'];

/***/ }),

/***/ "rxjs":
/*!*********************************!*\
  !*** external "window['rxjs']" ***!
  \*********************************/
/***/ ((module) => {

module.exports = window['rxjs'];

/***/ }),

/***/ "rxjs/operators":
/*!**********************************************!*\
  !*** external "window['rxjs']['operators']" ***!
  \**********************************************/
/***/ ((module) => {

module.exports = window['rxjs']['operators'];

/***/ })

/******/ 	});
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId](module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = __webpack_modules__;
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/async module */
/******/ 	(() => {
/******/ 		var webpackThen = typeof Symbol === "function" ? Symbol("webpack then") : "__webpack_then__";
/******/ 		var webpackExports = typeof Symbol === "function" ? Symbol("webpack exports") : "__webpack_exports__";
/******/ 		var completeQueue = (queue) => {
/******/ 			if(queue) {
/******/ 				queue.forEach((fn) => (fn.r--));
/******/ 				queue.forEach((fn) => (fn.r-- ? fn.r++ : fn()));
/******/ 			}
/******/ 		}
/******/ 		var completeFunction = (fn) => (!--fn.r && fn());
/******/ 		var queueFunction = (queue, fn) => (queue ? queue.push(fn) : completeFunction(fn));
/******/ 		var wrapDeps = (deps) => (deps.map((dep) => {
/******/ 			if(dep !== null && typeof dep === "object") {
/******/ 				if(dep[webpackThen]) return dep;
/******/ 				if(dep.then) {
/******/ 					var queue = [];
/******/ 					dep.then((r) => {
/******/ 						obj[webpackExports] = r;
/******/ 						completeQueue(queue);
/******/ 						queue = 0;
/******/ 					});
/******/ 					var obj = { [webpackThen]: (fn, reject) => (queueFunction(queue, fn), dep.catch(reject)) };
/******/ 					return obj;
/******/ 				}
/******/ 			}
/******/ 			return { [webpackThen]: (fn) => (completeFunction(fn)), [webpackExports]: dep };
/******/ 		}));
/******/ 		__webpack_require__.a = (module, body, hasAwait) => {
/******/ 			var queue = hasAwait && [];
/******/ 			var exports = module.exports;
/******/ 			var currentDeps;
/******/ 			var outerResolve;
/******/ 			var reject;
/******/ 			var isEvaluating = true;
/******/ 			var nested = false;
/******/ 			var whenAll = (deps, onResolve, onReject) => {
/******/ 				if (nested) return;
/******/ 				nested = true;
/******/ 				onResolve.r += deps.length;
/******/ 				deps.map((dep, i) => (dep[webpackThen](onResolve, onReject)));
/******/ 				nested = false;
/******/ 			};
/******/ 			var promise = new Promise((resolve, rej) => {
/******/ 				reject = rej;
/******/ 				outerResolve = () => (resolve(exports), completeQueue(queue), queue = 0);
/******/ 			});
/******/ 			promise[webpackExports] = exports;
/******/ 			promise[webpackThen] = (fn, rejectFn) => {
/******/ 				if (isEvaluating) { return completeFunction(fn); }
/******/ 				if (currentDeps) whenAll(currentDeps, fn, rejectFn);
/******/ 				queueFunction(queue, fn);
/******/ 				promise.catch(rejectFn);
/******/ 			};
/******/ 			module.exports = promise;
/******/ 			body((deps) => {
/******/ 				if(!deps) return outerResolve();
/******/ 				currentDeps = wrapDeps(deps);
/******/ 				var fn, result;
/******/ 				var promise = new Promise((resolve, reject) => {
/******/ 					fn = () => (resolve(result = currentDeps.map((d) => (d[webpackExports]))));
/******/ 					fn.r = 0;
/******/ 					whenAll(currentDeps, fn, reject);
/******/ 				});
/******/ 				return fn.r ? promise : result;
/******/ 			}).then(outerResolve, reject);
/******/ 			isEvaluating = false;
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/compat get default export */
/******/ 	(() => {
/******/ 		// getDefaultExport function for compatibility with non-harmony modules
/******/ 		__webpack_require__.n = (module) => {
/******/ 			var getter = module && module.__esModule ?
/******/ 				() => (module['default']) :
/******/ 				() => (module);
/******/ 			__webpack_require__.d(getter, { a: getter });
/******/ 			return getter;
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/define property getters */
/******/ 	(() => {
/******/ 		// define getter functions for harmony exports
/******/ 		__webpack_require__.d = (exports, definition) => {
/******/ 			for(var key in definition) {
/******/ 				if(__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
/******/ 					Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
/******/ 				}
/******/ 			}
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/ensure chunk */
/******/ 	(() => {
/******/ 		__webpack_require__.f = {};
/******/ 		// This file contains only the entry chunk.
/******/ 		// The chunk loading function for additional chunks
/******/ 		__webpack_require__.e = (chunkId) => {
/******/ 			return Promise.all(Object.keys(__webpack_require__.f).reduce((promises, key) => {
/******/ 				__webpack_require__.f[key](chunkId, promises);
/******/ 				return promises;
/******/ 			}, []));
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/get javascript chunk filename */
/******/ 	(() => {
/******/ 		// This function allow to reference async chunks
/******/ 		__webpack_require__.u = (chunkId) => {
/******/ 			// return url for filenames based on template
/******/ 			return "" + chunkId + "." + {"vendors-node_modules_d3-drag_src_drag_js-node_modules_tslib_tslib_es6_js":"732975441c3d68e3e000","on-load_ts":"0a06c33e9cf2e5fbde23"}[chunkId] + ".js";
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/get mini-css chunk filename */
/******/ 	(() => {
/******/ 		// This function allow to reference all chunks
/******/ 		__webpack_require__.miniCssF = (chunkId) => {
/******/ 			// return url for filenames based on template
/******/ 			return undefined;
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/global */
/******/ 	(() => {
/******/ 		__webpack_require__.g = (function() {
/******/ 			if (typeof globalThis === 'object') return globalThis;
/******/ 			try {
/******/ 				return this || new Function('return this')();
/******/ 			} catch (e) {
/******/ 				if (typeof window === 'object') return window;
/******/ 			}
/******/ 		})();
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/hasOwnProperty shorthand */
/******/ 	(() => {
/******/ 		__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop))
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/load script */
/******/ 	(() => {
/******/ 		var inProgress = {};
/******/ 		// data-webpack is not used as build has no uniqueName
/******/ 		// loadScript function to load a script via script tag
/******/ 		__webpack_require__.l = (url, done, key, chunkId) => {
/******/ 			if(inProgress[url]) { inProgress[url].push(done); return; }
/******/ 			var script, needAttach;
/******/ 			if(key !== undefined) {
/******/ 				var scripts = document.getElementsByTagName("script");
/******/ 				for(var i = 0; i < scripts.length; i++) {
/******/ 					var s = scripts[i];
/******/ 					if(s.getAttribute("src") == url) { script = s; break; }
/******/ 				}
/******/ 			}
/******/ 			if(!script) {
/******/ 				needAttach = true;
/******/ 				script = document.createElement('script');
/******/ 		
/******/ 				script.charset = 'utf-8';
/******/ 				script.timeout = 120;
/******/ 				if (__webpack_require__.nc) {
/******/ 					script.setAttribute("nonce", __webpack_require__.nc);
/******/ 				}
/******/ 		
/******/ 				script.src = url;
/******/ 			}
/******/ 			inProgress[url] = [done];
/******/ 			var onScriptComplete = (prev, event) => {
/******/ 				// avoid mem leaks in IE.
/******/ 				script.onerror = script.onload = null;
/******/ 				clearTimeout(timeout);
/******/ 				var doneFns = inProgress[url];
/******/ 				delete inProgress[url];
/******/ 				script.parentNode && script.parentNode.removeChild(script);
/******/ 				doneFns && doneFns.forEach((fn) => (fn(event)));
/******/ 				if(prev) return prev(event);
/******/ 			}
/******/ 			;
/******/ 			var timeout = setTimeout(onScriptComplete.bind(null, undefined, { type: 'timeout', target: script }), 120000);
/******/ 			script.onerror = onScriptComplete.bind(null, script.onerror);
/******/ 			script.onload = onScriptComplete.bind(null, script.onload);
/******/ 			needAttach && document.head.appendChild(script);
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/make namespace object */
/******/ 	(() => {
/******/ 		// define __esModule on exports
/******/ 		__webpack_require__.r = (exports) => {
/******/ 			if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 				Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 			}
/******/ 			Object.defineProperty(exports, '__esModule', { value: true });
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/publicPath */
/******/ 	(() => {
/******/ 		var scriptUrl;
/******/ 		if (__webpack_require__.g.importScripts) scriptUrl = __webpack_require__.g.location + "";
/******/ 		var document = __webpack_require__.g.document;
/******/ 		if (!scriptUrl && document) {
/******/ 			if (document.currentScript)
/******/ 				scriptUrl = document.currentScript.src
/******/ 			if (!scriptUrl) {
/******/ 				var scripts = document.getElementsByTagName("script");
/******/ 				if(scripts.length) scriptUrl = scripts[scripts.length - 1].src
/******/ 			}
/******/ 		}
/******/ 		// When supporting browsers where an automatic publicPath is not supported you must specify an output.publicPath manually via configuration
/******/ 		// or pass an empty string ("") and set the __webpack_public_path__ variable from your code to use your own logic.
/******/ 		if (!scriptUrl) throw new Error("Automatic publicPath is not supported in this browser");
/******/ 		scriptUrl = scriptUrl.replace(/#.*$/, "").replace(/\?.*$/, "").replace(/\/[^\/]+$/, "/");
/******/ 		__webpack_require__.p = scriptUrl;
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/jsonp chunk loading */
/******/ 	(() => {
/******/ 		// no baseURI
/******/ 		
/******/ 		// object to store loaded and loading chunks
/******/ 		// undefined = chunk not loaded, null = chunk preloaded/prefetched
/******/ 		// [resolve, reject, Promise] = chunk loading, 0 = chunk loaded
/******/ 		var installedChunks = {
/******/ 			"main": 0
/******/ 		};
/******/ 		
/******/ 		__webpack_require__.f.j = (chunkId, promises) => {
/******/ 				// JSONP chunk loading for javascript
/******/ 				var installedChunkData = __webpack_require__.o(installedChunks, chunkId) ? installedChunks[chunkId] : undefined;
/******/ 				if(installedChunkData !== 0) { // 0 means "already installed".
/******/ 		
/******/ 					// a Promise means "currently loading".
/******/ 					if(installedChunkData) {
/******/ 						promises.push(installedChunkData[2]);
/******/ 					} else {
/******/ 						if(true) { // all chunks have JS
/******/ 							// setup Promise in chunk cache
/******/ 							var promise = new Promise((resolve, reject) => (installedChunkData = installedChunks[chunkId] = [resolve, reject]));
/******/ 							promises.push(installedChunkData[2] = promise);
/******/ 		
/******/ 							// start chunk loading
/******/ 							var url = __webpack_require__.p + __webpack_require__.u(chunkId);
/******/ 							// create error before stack unwound to get useful stacktrace later
/******/ 							var error = new Error();
/******/ 							var loadingEnded = (event) => {
/******/ 								if(__webpack_require__.o(installedChunks, chunkId)) {
/******/ 									installedChunkData = installedChunks[chunkId];
/******/ 									if(installedChunkData !== 0) installedChunks[chunkId] = undefined;
/******/ 									if(installedChunkData) {
/******/ 										var errorType = event && (event.type === 'load' ? 'missing' : event.type);
/******/ 										var realSrc = event && event.target && event.target.src;
/******/ 										error.message = 'Loading chunk ' + chunkId + ' failed.\n(' + errorType + ': ' + realSrc + ')';
/******/ 										error.name = 'ChunkLoadError';
/******/ 										error.type = errorType;
/******/ 										error.request = realSrc;
/******/ 										installedChunkData[1](error);
/******/ 									}
/******/ 								}
/******/ 							};
/******/ 							__webpack_require__.l(url, loadingEnded, "chunk-" + chunkId, chunkId);
/******/ 						} else installedChunks[chunkId] = 0;
/******/ 					}
/******/ 				}
/******/ 		};
/******/ 		
/******/ 		// no prefetching
/******/ 		
/******/ 		// no preloaded
/******/ 		
/******/ 		// no HMR
/******/ 		
/******/ 		// no HMR manifest
/******/ 		
/******/ 		// no on chunks loaded
/******/ 		
/******/ 		// install a JSONP callback for chunk loading
/******/ 		var webpackJsonpCallback = (parentChunkLoadingFunction, data) => {
/******/ 			var [chunkIds, moreModules, runtime] = data;
/******/ 			// add "moreModules" to the modules object,
/******/ 			// then flag all "chunkIds" as loaded and fire callback
/******/ 			var moduleId, chunkId, i = 0;
/******/ 			for(moduleId in moreModules) {
/******/ 				if(__webpack_require__.o(moreModules, moduleId)) {
/******/ 					__webpack_require__.m[moduleId] = moreModules[moduleId];
/******/ 				}
/******/ 			}
/******/ 			if(runtime) runtime(__webpack_require__);
/******/ 			if(parentChunkLoadingFunction) parentChunkLoadingFunction(data);
/******/ 			for(;i < chunkIds.length; i++) {
/******/ 				chunkId = chunkIds[i];
/******/ 				if(__webpack_require__.o(installedChunks, chunkId) && installedChunks[chunkId]) {
/******/ 					installedChunks[chunkId][0]();
/******/ 				}
/******/ 				installedChunks[chunkIds[i]] = 0;
/******/ 			}
/******/ 		
/******/ 		}
/******/ 		
/******/ 		var chunkLoadingGlobal = self["webpackChunk"] = self["webpackChunk"] || [];
/******/ 		chunkLoadingGlobal.forEach(webpackJsonpCallback.bind(null, 0));
/******/ 		chunkLoadingGlobal.push = webpackJsonpCallback.bind(null, chunkLoadingGlobal.push.bind(chunkLoadingGlobal));
/******/ 	})();
/******/ 	
/************************************************************************/
/******/ 	
/******/ 	// startup
/******/ 	// Load entry module and return exports
/******/ 	// This entry module used 'module' so it can't be inlined
/******/ 	var __webpack_exports__ = __webpack_require__("./main.ts");
/******/ 	
/******/ })()
;
//# sourceMappingURL=main.f6030f768a745c6c4fde.js.map