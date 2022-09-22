"use strict";
(self["webpackChunk"] = self["webpackChunk"] || []).push([
  ["on-load_ts"],
  {
    /***/ "./notifier.ts":
      /*!*********************!*\
  !*** ./notifier.ts ***!
  \*********************/
      /***/ (
        __unused_webpack_module,
        __webpack_exports__,
        __webpack_require__
      ) => {
        __webpack_require__.r(__webpack_exports__);
        /* harmony export */ __webpack_require__.d(__webpack_exports__, {
          /* harmony export */ Notifier: () => /* binding */ Notifier,
          /* harmony export */ plugNotifications: () =>
            /* binding */ plugNotifications,
          /* harmony export */
        });
        /* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ =
          __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
        /* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default =
          /*#__PURE__*/ __webpack_require__.n(
            _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__
          );
        /* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__ =
          __webpack_require__(/*! @youwol/flux-view */ "@youwol/flux-view");
        /* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_1___default =
          /*#__PURE__*/ __webpack_require__.n(
            _youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__
          );
        /* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2__ =
          __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
        /* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2___default =
          /*#__PURE__*/ __webpack_require__.n(
            rxjs_operators__WEBPACK_IMPORTED_MODULE_2__
          );

        /**
         * Most of this file is replicated from flux-builder => factorization needed
         */
        function plugNotifications(environment) {
          environment.errors$
            .pipe(
              (0, rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.filter)(
                (log) =>
                  log.error instanceof
                  _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ModuleError
              )
            )
            .subscribe((log) =>
              Notifier.error({
                message: log.error.message,
                title: log.error.module.Factory.id,
              })
            );
          environment.processes$.subscribe((p) => {
            let classesIcon = {
              [_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ProcessMessageKind
                .Scheduled]: "fas fa-clock px-2",
              [_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ProcessMessageKind
                .Started]: "fas fa-cog fa-spin px-2",
              [_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ProcessMessageKind
                .Succeeded]: "fas fa-check fv-text-success px-2",
              [_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ProcessMessageKind
                .Failed]: "fas fa-times fv-text-error px-2",
              [_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ProcessMessageKind
                .Log]: "fas fa-cog fa-spin px-2",
            };
            let doneMessages = [
              _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ProcessMessageKind
                .Succeeded,
              _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ProcessMessageKind
                .Failed,
            ];
            Notifier.notify({
              title: p.title,
              message: (0,
              _youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__.attr$)(
                p.messages$,
                (step) => step.text
              ),
              classIcon: (0,
              _youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__.attr$)(
                p.messages$,
                (step) => classesIcon[step.kind]
              ),
              timeout: p.messages$.pipe(
                (0, rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.filter)((m) =>
                  doneMessages.includes(m.kind)
                ),
                (0, rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.take)(1),
                (0, rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.delay)(1000)
              ),
            });
          });
        }
        /**
         * This class provides a notification system that popups message in the
         * HTML document.
         *
         * For now, only module's errors (ModuleError in flux-core) are handled.
         *
         * Notification can be associated to custom [[INotifierAction | action]]
         */
        class Notifier {
          constructor() {}
          /**
           * Popup a notification with level=='Info'
           *
           * @param message content
           * @param title title
           * @param actions available actions
           */
          static notify({ message, title, classIcon, timeout }) {
            Notifier.popup({
              message,
              title,
              classIcon,
              timeout,
              classBorder: "",
            });
          }
          /**
           * Popup a notification with level=='Error'
           *
           * @param message content
           * @param title title
           * @param actions available actions
           */
          static error({ message, title }) {
            Notifier.popup({
              message,
              title,
              classIcon: Notifier.classesIcon[4],
              classBorder: Notifier.classesBorder[4],
            });
          }
          /**
           * Popup a notification with level=='Warning'
           *
           * @param message content
           * @param title title
           * @param actions available actions
           */
          static warning({ message, title }) {
            Notifier.popup({
              message,
              title,
              classIcon: Notifier.classesIcon[3],
              classBorder: Notifier.classesBorder[3],
            });
          }
          static popup({ message, title, classIcon, classBorder, timeout }) {
            let view = {
              class: "m-2 p-2 my-1 bg-white rounded " + classBorder,
              style: { border: "solid" },
              children: [
                {
                  class: "fas fa-times",
                  style: { float: "right", cursor: "pointer" },
                  onclick: (event) => {
                    event.target.parentElement.remove();
                  },
                },
                {
                  class: "d-flex py-2 align-items-center",
                  children: [
                    { tag: "i", class: classIcon },
                    { tag: "span", class: "d-block", innerText: title },
                  ],
                },
                message
                  ? { tag: "span", class: "d-block px-2", innerText: message }
                  : {},
                {
                  class: "d-flex align-space-around mt-2 fv-pointer",
                },
              ],
              connectedCallback: (elem) => {
                timeout && timeout.subscribe(() => elem.remove());
              },
            };
            let div = (0,
            _youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__.render)(view);
            document.getElementById("notifications-container").appendChild(div);
          }
        }
        Notifier.classesIcon = {
          4: "fas fa-2x fa-exclamation-circle text-danger px-2 mt-auto mb-auto",
          3: "fas fa-2x fa-exclamation text-warning px-2 mt-auto mb-auto",
        };
        Notifier.classesBorder = {
          4: "border-danger",
          3: "border-warning",
        };

        /***/
      },

    /***/ "./on-load.ts":
      /*!********************!*\
  !*** ./on-load.ts ***!
  \********************/
      /***/ (
        __unused_webpack_module,
        __webpack_exports__,
        __webpack_require__
      ) => {
        __webpack_require__.r(__webpack_exports__);
        /* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ =
          __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
        /* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default =
          /*#__PURE__*/ __webpack_require__.n(
            _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__
          );
        /* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1__ =
          __webpack_require__(/*! rxjs */ "rxjs");
        /* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1___default =
          /*#__PURE__*/ __webpack_require__.n(
            rxjs__WEBPACK_IMPORTED_MODULE_1__
          );
        /* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2__ =
          __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
        /* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2___default =
          /*#__PURE__*/ __webpack_require__.n(
            rxjs_operators__WEBPACK_IMPORTED_MODULE_2__
          );
        /* harmony import */ var _notifier__WEBPACK_IMPORTED_MODULE_3__ =
          __webpack_require__(/*! ./notifier */ "./notifier.ts");
        __webpack_require__(/*! ./style.css */ "./style.css");

        // this variable has been defined in the main.ts to initiate displaying dependencies fetching
        const loadingScreen = window["fluRunnerLoadingScreen"];
        class ApplicationState {
          constructor() {
            this.environment =
              new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Environment({
                renderingWindow: window,
                executingWindow: window,
                console: { ...console, log: () => undefined },
              });
            this.subscriptionStore = new Map();
            this.project$ = new rxjs__WEBPACK_IMPORTED_MODULE_1__.Subject();
            this.workflow$ =
              new rxjs__WEBPACK_IMPORTED_MODULE_1__.ReplaySubject(1);
          }
          loadProjectById(projectId) {
            (0,
            _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.loadProjectDatabase$)(
              projectId,
              this.workflow$,
              this.subscriptionStore,
              this.environment,
              (cdnEvent) => loadingScreen.next(cdnEvent)
            )
              .pipe(
                (0, rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.map)(
                  ({ project }) => applySideEffects(project)
                )
              )
              .subscribe((project) => this.project$.next(project));
          }
          loadProjectByUrl(url) {
            (0, _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.loadProject$)(
              (0,
              _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.createObservableFromFetch)(
                new Request(url)
              ),
              this.workflow$,
              this.subscriptionStore,
              this.environment,
              (cdnEvent) => loadingScreen.next(cdnEvent)
            )
              .pipe(
                (0, rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.map)(
                  ({ project }) => applySideEffects(project)
                )
              )
              .subscribe((project) => this.project$.next(project));
          }
        }
        function applySideEffects(project) {
          const wf = project.workflow;
          [...wf.plugins, ...wf.modules].forEach(
            (m) =>
              (0,
              _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.instanceOfSideEffects)(
                m
              ) && m.apply()
          );
          return project;
        }
        function run(state) {
          state.project$.subscribe((project) => {
            loadingScreen.done();
            const rootComponent = project.workflow.modules.find(
              (mdle) =>
                mdle.moduleId ==
                _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Component
                  .rootComponentId
            );
            const style = document.createElement("style");
            style.textContent = rootComponent.getFullCSS(project.workflow, {
              asString: true,
            });
            document.head.append(style);
            const contentDiv = document.getElementById("content");
            contentDiv.appendChild(rootComponent.getOuterHTML());
            (0, _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.renderTemplate)(
              contentDiv,
              [rootComponent]
            );
            applyHackRemoveDefaultStyles();
            const allSubscriptions = new Map();
            const allModules = [
              ...project.workflow.modules,
              ...project.workflow.plugins,
            ];
            (0,
            _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.subscribeConnections)(
              allModules,
              project.workflow.connections,
              allSubscriptions
            );
          });
        }
        const appState = new ApplicationState();
        appState.loadProjectByUrl("project.json");
        (0, _notifier__WEBPACK_IMPORTED_MODULE_3__.plugNotifications)(
          appState.environment
        );
        run(appState);
        function applyHackRemoveDefaultStyles() {
          /**
           * When defining ModuleFlux with views it is possible to associated default style.
           * Those default styles actually get higher priority than properties defined by grapes
           * using '#module-id{ ... }' => we remove the default.
           * Need to find a better way to associated default styles.
           * For modules replicated afterward, this hack is not working.
           */
          const fluxElements = document.querySelectorAll(".flux-element");
          Array.from(fluxElements).forEach((element) => {
            element.style.removeProperty("height");
            element.style.removeProperty("width");
          });
        }

        /***/
      },
  },
]);
//# sourceMappingURL=on-load_ts.fdb7e88f67ac0ae6bc0d.js.map
