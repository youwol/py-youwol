(()=>{"use strict";var e,r,n,t,o,i,a,c,d,s,l,u={897:(e,r,n)=>{n.r(r);var t=n(62)(e.id,{locals:!1});e.hot.dispose(t),e.hot.accept(void 0,t)},62:(e,r,n)=>{var t=n(373),o=Object.create(null),i="undefined"==typeof document,a=Array.prototype.forEach;function c(){}function d(e,r){if(!r){if(!e.href)return;r=e.href.split("?")[0]}if(l(r)&&!1!==e.isLoaded&&r&&r.indexOf(".css")>-1){e.visited=!0;var n=e.cloneNode();n.isLoaded=!1,n.addEventListener("load",(function(){n.isLoaded||(n.isLoaded=!0,e.parentNode.removeChild(e))})),n.addEventListener("error",(function(){n.isLoaded||(n.isLoaded=!0,e.parentNode.removeChild(e))})),n.href="".concat(r,"?").concat(Date.now()),e.nextSibling?e.parentNode.insertBefore(n,e.nextSibling):e.parentNode.appendChild(n)}}function s(){var e=document.querySelectorAll("link");a.call(e,(function(e){!0!==e.visited&&d(e)}))}function l(e){return!!/^https?:/i.test(e)}e.exports=function(e,r){if(i)return console.log("no window.document found, will not HMR CSS"),c;var n,u,f=function(e){var r=o[e];if(!r){if(document.currentScript)r=document.currentScript.src;else{var n=document.getElementsByTagName("script"),i=n[n.length-1];i&&(r=i.src)}o[e]=r}return function(e){if(!r)return null;var n=r.split(/([^\\/]+)\.js$/),o=n&&n[1];return o&&e?e.split(",").map((function(e){var n=new RegExp("".concat(o,"\\.js$"),"g");return t(r.replace(n,"".concat(e.replace(/{fileName}/g,o),".css")))})):[r.replace(".js",".css")]}}(e);return n=function(){var e=f(r.filename),n=function(e){if(!e)return!1;var r=document.querySelectorAll("link"),n=!1;return a.call(r,(function(r){if(r.href){var o=function(e,r){var n;return e=t(e,{stripWWW:!1}),r.some((function(t){e.indexOf(r)>-1&&(n=t)})),n}(r.href,e);l(o)&&!0!==r.visited&&o&&(d(r,o),n=!0)}})),n}(e);if(r.locals)return console.log("[HMR] Detected local css modules. Reload all css"),void s();n?console.log("[HMR] css reload %s",e.join(" ")):(console.log("[HMR] Reload all css"),s())},50,u=0,function(){var e=this,r=arguments,t=function(){return n.apply(e,r)};clearTimeout(u),u=setTimeout(t,50)}}},373:e=>{e.exports=function(e){if(e=e.trim(),/^data:/i.test(e))return e;var r=-1!==e.indexOf("//")?e.split("//")[0]+"//":"",n=e.replace(new RegExp(r,"i"),"").split("/"),t=n[0].toLowerCase().replace(/\.$/,"");return n[0]="",r+t+n.reduce((function(e,r){switch(r){case"..":e.pop();break;case".":break;default:e.push(r)}return e}),[]).join("/")}},983:(e,r,n)=>{n.a(e,(async e=>{n(897);let r=window["@youwol/cdn-client"];await r.fetchStyleSheets(["bootstrap#4.4.1~bootstrap.min.css","fontawesome#5.12.1~css/all.min.css","@youwol/fv-widgets#0.0.3~dist/assets/styles/style.youwol.css","codemirror#5.52.0~codemirror.min.css","codemirror#5.52.0~theme/blackboard.min.css"]),await r.fetchBundles({d3:"5.15.0",lodash:"4.17.15","@youwol/flux-view":"latest","@youwol/fv-group":"latest","@youwol/fv-input":"latest","@youwol/fv-button":"latest","@youwol/fv-tree":"latest","@youwol/fv-tabs":"latest","@youwol/flux-youwol-essentials":"latest","@youwol/flux-files":"latest",rxjs:"6.5.5"},window),await r.fetchJavascriptAddOn(["codemirror#5.52.0~codemirror.min.js"]),await r.fetchJavascriptAddOn(["codemirror#5.52.0~mode/python.min.js"]),await n.e(870).then(n.bind(n,870)),e()}),1)},435:e=>{e.exports=rxjs},71:e=>{e.exports=window["@youwol/flux-files"]},222:e=>{e.exports=window["@youwol/flux-view"]},444:e=>{e.exports=window["@youwol/flux-youwol-essentials"]},327:e=>{e.exports=window["@youwol/fv-button"]},337:e=>{e.exports=window["@youwol/fv-group"]},313:e=>{e.exports=window["@youwol/fv-input"]},690:e=>{e.exports=window["@youwol/fv-tabs"]},888:e=>{e.exports=window["@youwol/fv-tree"]},519:e=>{e.exports=window.rxjs.operators}},f={};function p(e){var r=f[e];if(void 0!==r){if(void 0!==r.error)throw r.error;return r.exports}var n=f[e]={id:e,exports:{}};try{var t={id:e,module:n,factory:u[e],require:p};p.i.forEach((function(e){e(t)})),n=t.module,t.factory.call(n.exports,n,n.exports,t.require)}catch(e){throw n.error=e,e}return n.exports}p.m=u,p.c=f,p.i=[],e="function"==typeof Symbol?Symbol("webpack then"):"__webpack_then__",r="function"==typeof Symbol?Symbol("webpack exports"):"__webpack_exports__",n=e=>{e&&(e.forEach((e=>e.r--)),e.forEach((e=>e.r--?e.r++:e())))},t=e=>!--e.r&&e(),o=(e,r)=>e?e.push(r):t(r),p.a=(i,a,c)=>{var d,s,l,u=c&&[],f=i.exports,p=!0,h=!1,v=(r,n,t)=>{h||(h=!0,n.r+=r.length,r.map(((r,o)=>r[e](n,t))),h=!1)},m=new Promise(((e,r)=>{l=r,s=()=>(e(f),n(u),u=0)}));m[r]=f,m[e]=(e,r)=>{if(p)return t(e);d&&v(d,e,r),o(u,e),m.catch(r)},i.exports=m,a((i=>{if(!i)return s();var a,c;d=(i=>i.map((i=>{if(null!==i&&"object"==typeof i){if(i[e])return i;if(i.then){var a=[];i.then((e=>{c[r]=e,n(a),a=0}));var c={[e]:(e,r)=>(o(a,e),i.catch(r))};return c}}return{[e]:e=>t(e),[r]:i}})))(i);var l=new Promise(((e,n)=>{(a=()=>e(c=d.map((e=>e[r])))).r=0,v(d,a,n)}));return a.r?l:c})).then(s,l),p=!1},p.f={},p.e=e=>Promise.all(Object.keys(p.f).reduce(((r,n)=>(p.f[n](e,r),r)),[])),p.u=e=>e+".376e5d1349660653acf6.js",p.hu=e=>e+"."+p.h()+".hot-update.js",p.miniCssF=e=>{},p.hmrF=()=>"main."+p.h()+".hot-update.json",p.h=()=>"b8348e80d3f1d7ceab67",p.g=function(){if("object"==typeof globalThis)return globalThis;try{return this||new Function("return this")()}catch(e){if("object"==typeof window)return window}}(),p.o=(e,r)=>Object.prototype.hasOwnProperty.call(e,r),i={},p.l=(e,r,n,t)=>{if(i[e])i[e].push(r);else{var o,a;if(void 0!==n)for(var c=document.getElementsByTagName("script"),d=0;d<c.length;d++){var s=c[d];if(s.getAttribute("src")==e){o=s;break}}o||(a=!0,(o=document.createElement("script")).charset="utf-8",o.timeout=120,p.nc&&o.setAttribute("nonce",p.nc),o.src=e),i[e]=[r];var l=(r,n)=>{o.onerror=o.onload=null,clearTimeout(u);var t=i[e];if(delete i[e],o.parentNode&&o.parentNode.removeChild(o),t&&t.forEach((e=>e(n))),r)return r(n)},u=setTimeout(l.bind(null,void 0,{type:"timeout",target:o}),12e4);o.onerror=l.bind(null,o.onerror),o.onload=l.bind(null,o.onload),a&&document.head.appendChild(o)}},p.r=e=>{"undefined"!=typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(e,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(e,"__esModule",{value:!0})},(()=>{var e,r,n,t,o={},i=p.c,a=[],c=[],d="idle";function s(e){d=e;for(var r=0;r<c.length;r++)c[r].call(null,e)}function l(e){if(0===r.length)return e();var n=r;return r=[],Promise.all(n).then((function(){return l(e)}))}function u(e){if("idle"!==d)throw new Error("check() is only allowed in idle status");return s("check"),p.hmrM().then((function(t){if(!t)return s(v()?"ready":"idle"),null;s("prepare");var o=[];return r=[],n=[],Promise.all(Object.keys(p.hmrC).reduce((function(e,r){return p.hmrC[r](t.c,t.r,t.m,e,n,o),e}),[])).then((function(){return l((function(){return e?h(e):(s("ready"),o)}))}))}))}function f(e){return"ready"!==d?Promise.resolve().then((function(){throw new Error("apply() is only allowed in ready status")})):h(e)}function h(e){e=e||{},v();var r=n.map((function(r){return r(e)}));n=void 0;var o,i=r.map((function(e){return e.error})).filter(Boolean);if(i.length>0)return s("abort"),Promise.resolve().then((function(){throw i[0]}));s("dispose"),r.forEach((function(e){e.dispose&&e.dispose()})),s("apply");var a=function(e){o||(o=e)},c=[];return r.forEach((function(e){if(e.apply){var r=e.apply(a);if(r)for(var n=0;n<r.length;n++)c.push(r[n])}})),o?(s("fail"),Promise.resolve().then((function(){throw o}))):t?h(e).then((function(e){return c.forEach((function(r){e.indexOf(r)<0&&e.push(r)})),e})):(s("idle"),Promise.resolve(c))}function v(){if(t)return n||(n=[]),Object.keys(p.hmrI).forEach((function(e){t.forEach((function(r){p.hmrI[e](r,n)}))})),t=void 0,!0}p.hmrD=o,p.i.push((function(h){var v,m,y,w=h.module,g=function(n,t){var o=i[t];if(!o)return n;var c=function(r){if(o.hot.active){if(i[r]){var c=i[r].parents;-1===c.indexOf(t)&&c.push(t)}else a=[t],e=r;-1===o.children.indexOf(r)&&o.children.push(r)}else console.warn("[HMR] unexpected require("+r+") from disposed module "+t),a=[];return n(r)},u=function(e){return{configurable:!0,enumerable:!0,get:function(){return n[e]},set:function(r){n[e]=r}}};for(var f in n)Object.prototype.hasOwnProperty.call(n,f)&&"e"!==f&&Object.defineProperty(c,f,u(f));return c.e=function(e){return function(e){switch(d){case"ready":return s("prepare"),r.push(e),l((function(){s("ready")})),e;case"prepare":return r.push(e),e;default:return e}}(n.e(e))},c}(h.require,h.id);w.hot=(v=h.id,m=w,y={_acceptedDependencies:{},_acceptedErrorHandlers:{},_declinedDependencies:{},_selfAccepted:!1,_selfDeclined:!1,_selfInvalidated:!1,_disposeHandlers:[],_main:e!==v,_requireSelf:function(){a=m.parents.slice(),e=v,p(v)},active:!0,accept:function(e,r,n){if(void 0===e)y._selfAccepted=!0;else if("function"==typeof e)y._selfAccepted=e;else if("object"==typeof e&&null!==e)for(var t=0;t<e.length;t++)y._acceptedDependencies[e[t]]=r||function(){},y._acceptedErrorHandlers[e[t]]=n;else y._acceptedDependencies[e]=r||function(){},y._acceptedErrorHandlers[e]=n},decline:function(e){if(void 0===e)y._selfDeclined=!0;else if("object"==typeof e&&null!==e)for(var r=0;r<e.length;r++)y._declinedDependencies[e[r]]=!0;else y._declinedDependencies[e]=!0},dispose:function(e){y._disposeHandlers.push(e)},addDisposeHandler:function(e){y._disposeHandlers.push(e)},removeDisposeHandler:function(e){var r=y._disposeHandlers.indexOf(e);r>=0&&y._disposeHandlers.splice(r,1)},invalidate:function(){switch(this._selfInvalidated=!0,d){case"idle":n=[],Object.keys(p.hmrI).forEach((function(e){p.hmrI[e](v,n)})),s("ready");break;case"ready":Object.keys(p.hmrI).forEach((function(e){p.hmrI[e](v,n)}));break;case"prepare":case"check":case"dispose":case"apply":(t=t||[]).push(v)}},check:u,apply:f,status:function(e){if(!e)return d;c.push(e)},addStatusHandler:function(e){c.push(e)},removeStatusHandler:function(e){var r=c.indexOf(e);r>=0&&c.splice(r,1)},data:o[v]},e=void 0,y),w.parents=a,w.children=[],a=[],h.require=g})),p.hmrC={},p.hmrI={}})(),(()=>{var e;p.g.importScripts&&(e=p.g.location+"");var r=p.g.document;if(!e&&r&&(r.currentScript&&(e=r.currentScript.src),!e)){var n=r.getElementsByTagName("script");n.length&&(e=n[n.length-1].src)}if(!e)throw new Error("Automatic publicPath is not supported in this browser");e=e.replace(/#.*$/,"").replace(/\?.*$/,"").replace(/\/[^\/]+$/,"/"),p.p=e})(),a=(e,r,n,t)=>{var o=document.createElement("link");o.rel="stylesheet",o.type="text/css",o.onerror=o.onload=i=>{if(o.onerror=o.onload=null,"load"===i.type)n();else{var a=i&&("load"===i.type?"missing":i.type),c=i&&i.target&&i.target.href||r,d=new Error("Loading CSS chunk "+e+" failed.\n("+c+")");d.code="CSS_CHUNK_LOAD_FAILED",d.type=a,d.request=c,o.parentNode.removeChild(o),t(d)}},o.href=r;var i=document.querySelector("#css-anchor");return i.parentNode.insertBefore(o,i.nextSibling),o},c=(e,r)=>{for(var n=document.getElementsByTagName("link"),t=0;t<n.length;t++){var o=(a=n[t]).getAttribute("data-href")||a.getAttribute("href");if("stylesheet"===a.rel&&(o===e||o===r))return a}var i=document.getElementsByTagName("style");for(t=0;t<i.length;t++){var a;if((o=(a=i[t]).getAttribute("data-href"))===e||o===r)return a}},d=[],s=[],l=e=>({dispose:()=>{for(var e=0;e<d.length;e++){var r=d[e];r.parentNode&&r.parentNode.removeChild(r)}d.length=0},apply:()=>{for(var e=0;e<s.length;e++)s[e].rel="stylesheet";s.length=0}}),p.hmrC.miniCss=(e,r,n,t,o,i)=>{o.push(l),e.forEach((e=>{var r=p.miniCssF(e),n=p.p+r;const o=c(r,n);o&&t.push(new Promise(((r,t)=>{var i=a(e,n,(()=>{i.as="style",i.rel="preload",r()}),t);d.push(o),s.push(i)})))}))},(()=>{var e={179:0};p.f.j=(r,n)=>{var t=p.o(e,r)?e[r]:void 0;if(0!==t)if(t)n.push(t[2]);else{var o=new Promise(((n,o)=>t=e[r]=[n,o]));n.push(t[2]=o);var i=p.p+p.u(r),a=new Error;p.l(i,(n=>{if(p.o(e,r)&&(0!==(t=e[r])&&(e[r]=void 0),t)){var o=n&&("load"===n.type?"missing":n.type),i=n&&n.target&&n.target.src;a.message="Loading chunk "+r+" failed.\n("+o+": "+i+")",a.name="ChunkLoadError",a.type=o,a.request=i,t[1](a)}}),"chunk-"+r,r)}};var r,n,t,o,i={};function a(e){return new Promise(((r,n)=>{i[e]=r;var t=p.p+p.hu(e),o=new Error;p.l(t,(r=>{if(i[e]){i[e]=void 0;var t=r&&("load"===r.type?"missing":r.type),a=r&&r.target&&r.target.src;o.message="Loading hot update chunk "+e+" failed.\n("+t+": "+a+")",o.name="ChunkLoadError",o.type=t,o.request=a,n(o)}}))}))}function c(i){function a(e){for(var r=[e],n={},t=r.map((function(e){return{chain:[e],id:e}}));t.length>0;){var o=t.pop(),i=o.id,a=o.chain,d=p.c[i];if(d&&(!d.hot._selfAccepted||d.hot._selfInvalidated)){if(d.hot._selfDeclined)return{type:"self-declined",chain:a,moduleId:i};if(d.hot._main)return{type:"unaccepted",chain:a,moduleId:i};for(var s=0;s<d.parents.length;s++){var l=d.parents[s],u=p.c[l];if(u){if(u.hot._declinedDependencies[i])return{type:"declined",chain:a.concat([l]),moduleId:i,parentId:l};-1===r.indexOf(l)&&(u.hot._acceptedDependencies[i]?(n[l]||(n[l]=[]),c(n[l],[i])):(delete n[l],r.push(l),t.push({chain:a.concat([l]),id:l})))}}}}return{type:"accepted",moduleId:e,outdatedModules:r,outdatedDependencies:n}}function c(e,r){for(var n=0;n<r.length;n++){var t=r[n];-1===e.indexOf(t)&&e.push(t)}}p.f&&delete p.f.jsonpHmr,r=void 0;var d={},s=[],l={},u=function(e){console.warn("[HMR] unexpected require("+e.id+") to disposed module")};for(var f in n)if(p.o(n,f)){var h,v=n[f],m=!1,y=!1,w=!1,g="";switch((h=v?a(f):{type:"disposed",moduleId:f}).chain&&(g="\nUpdate propagation: "+h.chain.join(" -> ")),h.type){case"self-declined":i.onDeclined&&i.onDeclined(h),i.ignoreDeclined||(m=new Error("Aborted because of self decline: "+h.moduleId+g));break;case"declined":i.onDeclined&&i.onDeclined(h),i.ignoreDeclined||(m=new Error("Aborted because of declined dependency: "+h.moduleId+" in "+h.parentId+g));break;case"unaccepted":i.onUnaccepted&&i.onUnaccepted(h),i.ignoreUnaccepted||(m=new Error("Aborted because "+f+" is not accepted"+g));break;case"accepted":i.onAccepted&&i.onAccepted(h),y=!0;break;case"disposed":i.onDisposed&&i.onDisposed(h),w=!0;break;default:throw new Error("Unexception type "+h.type)}if(m)return{error:m};if(y)for(f in l[f]=v,c(s,h.outdatedModules),h.outdatedDependencies)p.o(h.outdatedDependencies,f)&&(d[f]||(d[f]=[]),c(d[f],h.outdatedDependencies[f]));w&&(c(s,[h.moduleId]),l[f]=u)}n=void 0;for(var b,E=[],x=0;x<s.length;x++){var _=s[x],k=p.c[_];k&&k.hot._selfAccepted&&l[_]!==u&&!k.hot._selfInvalidated&&E.push({module:_,require:k.hot._requireSelf,errorHandler:k.hot._selfAccepted})}return{dispose:function(){var r;t.forEach((function(r){delete e[r]})),t=void 0;for(var n,o=s.slice();o.length>0;){var i=o.pop(),a=p.c[i];if(a){var c={},l=a.hot._disposeHandlers;for(x=0;x<l.length;x++)l[x].call(null,c);for(p.hmrD[i]=c,a.hot.active=!1,delete p.c[i],delete d[i],x=0;x<a.children.length;x++){var u=p.c[a.children[x]];u&&(r=u.parents.indexOf(i))>=0&&u.parents.splice(r,1)}}}for(var f in d)if(p.o(d,f)&&(a=p.c[f]))for(b=d[f],x=0;x<b.length;x++)n=b[x],(r=a.children.indexOf(n))>=0&&a.children.splice(r,1)},apply:function(e){for(var r in l)p.o(l,r)&&(p.m[r]=l[r]);for(var n=0;n<o.length;n++)o[n](p);for(var t in d)if(p.o(d,t)){var a=p.c[t];if(a){b=d[t];for(var c=[],u=[],f=[],h=0;h<b.length;h++){var v=b[h],m=a.hot._acceptedDependencies[v],y=a.hot._acceptedErrorHandlers[v];if(m){if(-1!==c.indexOf(m))continue;c.push(m),u.push(y),f.push(v)}}for(var w=0;w<c.length;w++)try{c[w].call(null,b)}catch(r){if("function"==typeof u[w])try{u[w](r,{moduleId:t,dependencyId:f[w]})}catch(n){i.onErrored&&i.onErrored({type:"accept-error-handler-errored",moduleId:t,dependencyId:f[w],error:n,originalError:r}),i.ignoreErrored||(e(n),e(r))}else i.onErrored&&i.onErrored({type:"accept-errored",moduleId:t,dependencyId:f[w],error:r}),i.ignoreErrored||e(r)}}}for(var g=0;g<E.length;g++){var x=E[g],_=x.module;try{x.require(_)}catch(r){if("function"==typeof x.errorHandler)try{x.errorHandler(r,{moduleId:_,module:p.c[_]})}catch(n){i.onErrored&&i.onErrored({type:"self-accept-error-handler-errored",moduleId:_,error:n,originalError:r}),i.ignoreErrored||(e(n),e(r))}else i.onErrored&&i.onErrored({type:"self-accept-errored",moduleId:_,error:r}),i.ignoreErrored||e(r)}}return s}}}self.webpackHotUpdate=(e,r,t)=>{for(var a in r)p.o(r,a)&&(n[a]=r[a]);t&&o.push(t),i[e]&&(i[e](),i[e]=void 0)},p.hmrI.jsonp=function(e,r){n||(n={},o=[],t=[],r.push(c)),p.o(n,e)||(n[e]=p.m[e])},p.hmrC.jsonp=function(i,d,s,l,u,f){u.push(c),r={},t=d,n=s.reduce((function(e,r){return e[r]=!1,e}),{}),o=[],i.forEach((function(n){p.o(e,n)&&void 0!==e[n]&&(l.push(a(n)),r[n]=!0)})),p.f&&(p.f.jsonpHmr=function(n,t){r&&!p.o(r,n)&&p.o(e,n)&&void 0!==e[n]&&(t.push(a(n)),r[n]=!0)})},p.hmrM=()=>{if("undefined"==typeof fetch)throw new Error("No browser support: need fetch API");return fetch(p.p+p.hmrF()).then((e=>{if(404!==e.status){if(!e.ok)throw new Error("Failed to fetch update manifest "+e.statusText);return e.json()}}))};var d=(r,n)=>{var t,o,[i,a,c]=n,d=0;for(t in a)p.o(a,t)&&(p.m[t]=a[t]);for(c&&c(p),r&&r(n);d<i.length;d++)o=i[d],p.o(e,o)&&e[o]&&e[o][0](),e[i[d]]=0},s=self.webpackChunk=self.webpackChunk||[];s.forEach(d.bind(null,0)),s.push=d.bind(null,s.push.bind(s))})(),p(983)})();
//# sourceMappingURL=main.bd0ce53f5bf483996508.js.map