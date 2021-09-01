(self["webpackChunk"] = self["webpackChunk"] || []).push([["on-load_ts"],{

/***/ "./builder-editor/builder-plots/box-selector-plotter.ts":
/*!**************************************************************!*\
  !*** ./builder-editor/builder-plots/box-selector-plotter.ts ***!
  \**************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "BoxSelectorPlotter": () => (/* binding */ BoxSelectorPlotter)
/* harmony export */ });
/* harmony import */ var _builder_state_index__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../builder-state/index */ "./builder-editor/builder-state/index.ts");
/* harmony import */ var _drawing_utils__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./drawing-utils */ "./builder-editor/builder-plots/drawing-utils.ts");


class BoxSelectorPlotter {
    constructor(drawingArea, plottersObservables, appObservables, appStore, modulesPlotter) {
        this.drawingArea = drawingArea;
        this.plottersObservables = plottersObservables;
        this.appObservables = appObservables;
        this.appStore = appStore;
        this.modulesPlotter = modulesPlotter;
        this.debugSingleton = _builder_state_index__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
        this.start = undefined;
        this.rect = undefined;
    }
    startSelection(coordinates) {
        //this.appObservables.unselect$.next()
        coordinates = this.convert(coordinates);
        this.rect = this.drawingArea.drawingGroup
            .append("rect")
            .attr("class", "rectangle-selector")
            .attr("x", coordinates[0])
            .attr("y", coordinates[1])
            .attr("height", 0)
            .attr("width", 0);
        this.start = coordinates;
    }
    finishSelection(coordinates) {
        this.start = undefined;
        let modulesId = BoxSelectorPlotter.getSelectedModules(this.appStore.getActiveModulesView(), this.drawingArea, this.rect);
        let finalRect = (0,_drawing_utils__WEBPACK_IMPORTED_MODULE_1__.getBoundingBox)(modulesId, 10, this.drawingArea);
        this.rect /*.transition()
        .duration(500)
        .attr("x",finalRect.x)
        .attr("y",finalRect.y)
        .attr("width",finalRect.width)
        .attr("height",finalRect.height)*/
            .remove();
        this.appStore.select({
            modulesId: modulesId,
            connectionsId: []
        });
        //setTimeout(() => this.wfPlotter.setSelectionBox(modulesId), 500)
    }
    moveTo(coordinates) {
        if (!this.start)
            return;
        coordinates = this.convert(coordinates);
        this.rect.attr("width", Math.max(0, coordinates[0] - +this.rect.attr("x")))
            .attr("height", Math.max(0, coordinates[1] - +this.rect.attr("y")));
        let highlighteds = BoxSelectorPlotter.getSelectedModules(this.appStore.getActiveModulesView(), this.drawingArea, this.rect);
        this.modulesPlotter.highlight(highlighteds);
    }
    static getSelectedModules(modulesView, drawingArea, rect) {
        let coors = modulesView
            .map(m => [
            m.moduleId,
            drawingArea.hScale(m.xWorld),
            drawingArea.vScale(m.yWorld)
        ]);
        let x0 = Number(rect.attr("x"));
        let y0 = Number(rect.attr("y"));
        let x1 = x0 + Number(rect.attr("width"));
        let y1 = y0 + Number(rect.attr("height"));
        return coors
            .filter(([_, x, y]) => x > x0 && x < x1 && y > y0 && y < y1)
            .map(([mid, x, y]) => mid);
    }
    convert([x, y]) {
        let transform = this.drawingArea.overallTranform;
        return [(x - transform.translateX) / transform.scale, (y - transform.translateY) / transform.scale];
    }
}


/***/ }),

/***/ "./builder-editor/builder-plots/connections-plotter.ts":
/*!*************************************************************!*\
  !*** ./builder-editor/builder-plots/connections-plotter.ts ***!
  \*************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "ConnectionsPlotter": () => (/* binding */ ConnectionsPlotter)
/* harmony export */ });
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! @youwol/flux-svg-plots */ "@youwol/flux-svg-plots");
/* harmony import */ var _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3__);
/* harmony import */ var _models_view__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./models-view */ "./builder-editor/builder-plots/models-view.ts");
/* harmony import */ var _builder_state_index__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ../builder-state/index */ "./builder-editor/builder-state/index.ts");






let wirelessIcon = `
<linearGradient id="a" gradientTransform="matrix(1 0 0 -1 0 -22278)" gradientUnits="userSpaceOnUse" x1="0" x2="512" y1="-22534" y2="-22534"><stop offset="0" stop-color="#00f1ff"/><stop offset=".231" stop-color="#00d8ff"/><stop offset=".5138" stop-color="#00c0ff"/><stop offset=".7773" stop-color="#00b2ff"/><stop offset="1" stop-color="#00adff"/></linearGradient>
<path d="m512 256c0 141.386719-114.613281 256-256 256s-256-114.613281-256-256 114.613281-256 256-256 256 114.613281 256 256zm0 0" fill="url(#a)"/><g fill="#fff"><path d="m279.050781 385.15625c0 13.128906-10.640625 23.773438-23.769531 23.773438s-23.773438-10.644532-23.773438-23.773438 10.644532-23.769531 23.773438-23.769531 23.769531 10.640625 23.769531 23.769531zm0 0"/><path d="m85.996094 209.265625c-3.660156 0-7.332032-1.332031-10.222656-4.027344-6.058594-5.644531-6.394532-15.136719-.746094-21.199219 47.460937-50.921874 111.730468-78.964843 180.96875-78.964843 69.246094 0 133.515625 28.042969 180.976562 78.964843 5.648438 6.0625 5.3125 15.554688-.746094 21.199219-6.058593 5.652344-15.550781 5.316407-21.199218-.742187-41.726563-44.769532-98.203125-69.421875-159.023438-69.421875-60.832031 0-117.304687 24.652343-159.03125 69.421875-2.953125 3.167968-6.960937 4.769531-10.976562 4.769531zm0 0"/><path d="m138.582031 269.089844c-3.820312 0-7.640625-1.449219-10.566406-4.355469-5.878906-5.832031-5.914063-15.332031-.082031-21.210937 35.101562-35.375 80.582031-54.859376 128.0625-54.859376 47.472656 0 92.953125 19.480469 128.0625 54.859376 5.835937 5.878906 5.800781 15.375-.078125 21.210937-5.882813 5.835937-15.378907 5.800781-21.214844-.078125-29.433594-29.660156-67.351563-45.992188-106.769531-45.992188-39.421875 0-77.339844 16.332032-106.765625 45.988282-2.933594 2.957031-6.789063 4.4375-10.648438 4.4375zm0 0"/><path d="m315.84375 328.84375c-3.816406 0-7.632812-1.445312-10.558594-4.34375-13.234375-13.113281-32.636718-21.589844-49.421875-21.589844-.003906 0-.003906 0-.007812 0h-1.039063c-.003906 0-.007812 0-.007812 0-16.789063 0-36.1875 8.472656-49.425782 21.589844-5.882812 5.828125-15.378906 5.785156-21.210937-.097656-5.832031-5.886719-5.789063-15.382813.097656-21.214844 18.847657-18.675781 45.875-30.277344 70.535157-30.277344h.011718 1.039063.011719c24.660156 0 51.683593 11.601563 70.535156 30.277344 5.882812 5.832031 5.929687 15.328125.097656 21.214844-2.933594 2.957031-6.796875 4.441406-10.65625 4.441406zm0 0"/></g>
`;
let svgAdaptorGroup = {
    tag: "g", class: 'adaptor', attributes: {},
    style: { visibility: 'visible' },
    children: [
        { tag: 'path', attributes: { d: "M211.331,190.817c-1.885-1.885-4.396-2.922-7.071-2.922c-2.675,0-5.186,1.038-7.07,2.922l-32.129,32.129l-24.403-24.403   l32.129-32.129c3.897-3.899,3.897-10.243-0.001-14.142l-11.125-11.125c-1.885-1.885-4.396-2.922-7.071-2.922   c-2.675,0-5.187,1.038-7.07,2.923l-32.128,32.128l-18.256-18.256c-1.885-1.885-4.396-2.922-7.071-2.922   c-2.675,0-5.186,1.038-7.07,2.922L66.95,171.062c-3.899,3.899-3.899,10.243,0,14.143l3.802,3.802   c-1.596,1.086-3.103,2.325-4.496,3.718l-46.679,46.679c-5.836,5.835-9.049,13.62-9.049,21.92c0,8.301,3.214,16.086,9.049,21.92   l17.943,17.943L5.126,333.582c-6.835,6.835-6.835,17.915,0,24.749c3.417,3.417,7.896,5.125,12.374,5.125s8.957-1.708,12.374-5.125   l32.395-32.395l18.091,18.091c5.834,5.835,13.619,9.048,21.92,9.048s16.086-3.213,21.92-9.048l46.679-46.679   c1.394-1.393,2.633-2.901,3.719-4.497l3.802,3.802c1.885,1.885,4.396,2.923,7.07,2.923c2.675,0,5.186-1.038,7.072-2.923   l16.04-16.042c1.887-1.885,2.925-4.396,2.925-7.072c0-2.676-1.038-5.187-2.924-7.071l-18.255-18.255l32.129-32.129   c3.898-3.899,3.898-10.244-0.001-14.142L211.331,190.817z" } },
        { tag: 'path', attributes: { d: "M358.33,5.126c-6.834-6.834-17.914-6.834-24.748,0l-32.686,32.686l-17.944-17.944c-5.834-5.835-13.619-9.048-21.92-9.048   c-8.301,0-16.086,3.213-21.92,9.048l-46.679,46.679c-1.393,1.393-2.632,2.9-3.719,4.497l-3.802-3.802   c-1.885-1.885-4.396-2.923-7.071-2.923c-2.675,0-5.187,1.038-7.071,2.923l-16.042,16.042c-1.886,1.885-2.924,4.396-2.924,7.072   c0,2.675,1.038,5.187,2.924,7.071l111.447,111.448c1.885,1.885,4.396,2.923,7.071,2.923c2.676,0,5.186-1.038,7.071-2.923   l16.043-16.043c3.899-3.899,3.899-10.243,0-14.142l-3.801-3.801c1.596-1.086,3.103-2.325,4.496-3.719l46.679-46.679   c5.835-5.834,9.049-13.62,9.049-21.92s-3.213-16.086-9.049-21.92l-18.09-18.09l32.686-32.686   C365.165,23.04,365.165,11.96,358.33,5.126z" } }
    ],
};
function connectionDisplay(d) {
    if (!d.data.adaptor) {
        let data = {
            tag: "g", attributes: { x1: d.x1, y1: d.y1, x2: d.x2, y2: d.y2 },
            children: {
                connection: { tag: "path", class: "connection-path", attributes: { d: `M${d.x1},${d.y1} C${0.5 * (d.x1 + d.x2)},${d.y1} ${0.5 * (d.x1 + d.x2)},${d.y2} ${d.x2},${d.y2}` } },
            }
        };
        return (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.createHTMLElement)({ data, namespace: "svg" });
    }
    let norm = Math.pow((d.x2 - d.x1) * (d.x2 - d.x1) + (d.y2 - d.y1) * (d.y2 - d.y1), 0.5);
    let cos_a = (d.x1 - d.x2) / norm;
    let sin_a = (d.y1 - d.y2) / norm;
    let angle = (-1 + 2 * Number(d.y2 < d.y1)) * Math.acos((d.x1 - d.x2) / norm) * 180 / 3.14;
    let x1 = d.x1 - 50 * cos_a;
    let y1 = d.y1 - 50 * sin_a;
    let gAdaptor = svgAdaptorGroup;
    gAdaptor.attributes = { transform: `translate(${-(d.x2 - d.x1) / 2 - 50 * cos_a},${-(d.y2 - d.y1) / 2 - 50 * sin_a} ) rotate(${angle + 45})  translate(-0,-36) scale(0.1)` };
    let data = {
        tag: "g", attributes: { x1: x1, y1: y1, x2: d.x2, y2: d.y2 },
        children: {
            connection: { tag: "path", class: "connection-path", attributes: { d: `M${d.x2},${d.y2} C${0.5 * (x1 + d.x2)},${d.y2} ${0.5 * (x1 + d.x2)},${0.5 * (y1 + d.y2)} ${x1},${y1}`, x1: x1, y1: y1, x2: d.x2, y2: d.y2 } },
            adaptor: gAdaptor,
        }
    };
    return (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.createHTMLElement)({ data, namespace: "svg" });
}
function getConnectionId(c) {
    return c.connectionId;
}
function retrieveSvgContainerGroup(moduleId, modulesGroup, appStore) {
    // when connection is between 2 different layers, the slot to connect with is included in the 'groupModule' 
    // that contains 'moduleId'
    let svgGroup = modulesGroup[moduleId];
    if (svgGroup)
        return svgGroup;
    let container = appStore.getParentGroupModule(moduleId);
    return container ? modulesGroup[container.moduleId] : undefined;
}
function toPlotterConnectionEntity(c, modulesGroup, appStore) {
    let props = appStore.project.builderRendering.connectionsView.find(cView => cView.connectionId == c.connectionId);
    return new _models_view__WEBPACK_IMPORTED_MODULE_4__.PlotterConnectionEntity(getConnectionId(c), ["connection", "mdle-color-stroke", (0,_youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3__.toCssName)(appStore.getModule(c.start.moduleId).Factory.uid)].concat(props && props.wireless ? ["wireless"] : []), retrieveSvgContainerGroup(c.end.moduleId, modulesGroup, appStore), retrieveSvgContainerGroup(c.start.moduleId, modulesGroup, appStore), c, c.adaptor);
}
function drawWirelessSlots(drawingArea, appStore) {
    let wirelesses = drawingArea.svgCanvas.node().querySelectorAll(".wireless");
    let drawingGroup = drawingArea.drawingGroup.node();
    let gPlugs = drawingGroup.querySelector("#wireless-slots");
    if (gPlugs)
        gPlugs.remove();
    gPlugs = document.createElementNS("http://www.w3.org/2000/svg", "g");
    gPlugs.id = "wireless-slots";
    drawingGroup.appendChild(gPlugs);
    wirelesses.forEach(g => {
        let selectFct = (event) => {
            event.stopPropagation();
            appStore.selectConnection(appStore.getConnection(g.id));
        };
        let delta = 25;
        let x1 = Number(g.getAttribute("x1"));
        let y1 = Number(g.getAttribute("y1"));
        let x2 = Number(g.getAttribute("x2"));
        let y2 = Number(g.getAttribute("y2"));
        const gplugStart = document.createElementNS("http://www.w3.org/2000/svg", "g");
        const gplugEnd = document.createElementNS("http://www.w3.org/2000/svg", "g");
        gplugStart.setAttribute("transform", g.getAttribute("transform"));
        gplugEnd.setAttribute("transform", g.getAttribute("transform"));
        gplugStart.innerHTML = `<line class='' x1="${x1}" y1="${y1}" x2="${Number(x1) - 50}" y2="${y1}"></line><g transform="translate(${x1 - 50 - 2 * delta},${y1 - delta}) scale(0.1)" > ${wirelessIcon}</g>`;
        gplugEnd.innerHTML = `<line class='' x1="${x2}" y1="${y2}" x2="${x2 + 50}" y2="${y2}"></line><g transform="translate(${x2 + 50},${y2 - delta}) scale(0.1)" > ${wirelessIcon}</g>`;
        gplugStart.onclick = selectFct;
        gplugEnd.onclick = selectFct;
        gPlugs.appendChild(gplugStart);
        gPlugs.appendChild(gplugEnd);
    });
}
function drawConnections(connections, modulesGroup, drawingArea, plotObservables$, appStore) {
    let connectionsPlotData = connections.map(c => toPlotterConnectionEntity(c, modulesGroup, appStore));
    let plot = new _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3__.LinkPlot({ plotId: "connectionsPlot",
        plotClasses: [],
        drawingArea: drawingArea,
        orderIndex: 3 });
    plot.defaultElementDisplay = connectionDisplay;
    plot.draw(connectionsPlotData);
    plot.entities$.subscribe(d => plotObservables$.next(d));
    drawWirelessSlots(drawingArea, appStore);
    return undefined;
}
function getSlot(mdle, domPlugElement, plugType) {
    let slotId = domPlugElement.getAttribute("slotId") || domPlugElement.getAttribute("slotid");
    let slot = mdle.getSlot(slotId);
    if (slot)
        return slot;
    if (mdle instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.GroupModules.Module && slotId) {
        // we end up here in case of slot corresponding to an implicit input of a group
        let moduleId = domPlugElement.getAttribute("moduleId") || domPlugElement.getAttribute("moduleid");
        return mdle.getAllChildren().find(mdle => mdle.moduleId == moduleId).getSlot(slotId);
    }
    console.warn("The builder plot should define the attribute 'slotId' of the slots elements", domPlugElement);
    // This section is for backward compatibility 06/15/2020
    slot = (plugType === "input") ?
        mdle.inputSlots.find(slot => domPlugElement.id === "input-slot_" + slot.slotId + "_" + slot.moduleId) :
        mdle.outputSlots.find(slot => domPlugElement.id === "output-slot_" + slot.slotId + "_" + slot.moduleId);
    return slot;
}
function getMdlWithGroup(plugSvgElement, appStore) {
    let containerSlot = plugSvgElement.parentElement;
    let mdl = appStore.getModuleOrPlugin(containerSlot.getAttribute("moduleId") || containerSlot.getAttribute("id"));
    if (!mdl) {
        containerSlot = containerSlot.parentElement;
        mdl = appStore.getModuleOrPlugin(containerSlot.getAttribute("moduleId") || containerSlot.getAttribute("id"));
    }
    return [mdl, containerSlot];
}
class DrawingConnection {
    constructor(mdle, domModuleElement, domPlugElement, plugType, isDrawing, isStarted) {
        this.mdle = mdle;
        this.domModuleElement = domModuleElement;
        this.domPlugElement = domPlugElement;
        this.plugType = plugType;
        this.isDrawing = isDrawing;
        this.isStarted = isStarted;
        this.xOrigin = undefined;
        this.yOrigin = undefined;
        this.slot = undefined;
        this.xOrigin = Number(domModuleElement.getAttribute("x")) + Number(domPlugElement.getAttribute("cx")),
            this.yOrigin = Number(domModuleElement.getAttribute("y")) + Number(domPlugElement.getAttribute("cy"));
        this.slot = getSlot(mdle, domPlugElement, plugType);
    }
}
class ConnectionsPlotter {
    constructor(drawingArea, plottersObservables, appObservables, appStore) {
        this.drawingArea = drawingArea;
        this.plottersObservables = plottersObservables;
        this.appObservables = appObservables;
        this.appStore = appStore;
        this.debugSingleton = _builder_state_index__WEBPACK_IMPORTED_MODULE_5__.AppDebugEnvironment.getInstance();
        this.connectionPlots = undefined;
        this.drawingConnection = undefined;
        // we don't want to create connection just after on finished, this is the purpose of this 
        // there should be better way to do using rxjs
        this.connectionCreationEnabled = true;
        let plotObservables$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.connectUserInteractions(plotObservables$);
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowView({
                level: _builder_state_index__WEBPACK_IMPORTED_MODULE_5__.LogLevel.Info,
                message: "create connections plotter",
                object: { drawingArea: drawingArea,
                    plottersObservables: plottersObservables }
            });
        (0,rxjs__WEBPACK_IMPORTED_MODULE_0__.combineLatest)(this.appObservables.connectionsUpdated$, this.plottersObservables.modulesDrawn$).subscribe(([connections, modulesGroup]) => {
            this.debugSingleton.debugOn &&
                this.debugSingleton.logWorkflowView({
                    level: _builder_state_index__WEBPACK_IMPORTED_MODULE_5__.LogLevel.Info,
                    message: "connections updated",
                    object: { connections: connections,
                        modulesGroup: modulesGroup }
                });
            drawConnections(appStore.project.workflow.connections, modulesGroup, this.drawingArea, plotObservables$, appStore);
            this.plottersObservables.connectionsDrawn$.next();
        });
        let startConnectionSubscription = (obs$, type) => {
            obs$.pipe(rxjs_operators__WEBPACK_IMPORTED_MODULE_1__.filter(_ => this.drawingConnection == undefined && this.connectionCreationEnabled)).subscribe((d) => {
                let [mdl, mdlGroup] = getMdlWithGroup(d.event.target, appStore);
                this.drawingConnection = new DrawingConnection(mdl, mdlGroup, d.event.target, type, true, false);
            });
        };
        let endConnectionSubscription = (obs$, type) => {
            obs$.pipe(rxjs_operators__WEBPACK_IMPORTED_MODULE_1__.filter(_ => this.drawingConnection != undefined &&
                this.drawingConnection.plugType == (type == "input" ? "output" : "input"))).subscribe((d) => {
                let [mdl, _] = getMdlWithGroup(d.event.target, appStore);
                let connection = type == "input" ?
                    new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Connection(this.drawingConnection.slot, getSlot(mdl, d.event.target, "input")) :
                    new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Connection(getSlot(mdl, d.event.target, "output"), this.drawingConnection.slot);
                this.appStore.addConnection(connection);
                this.connectionCreationEnabled = false;
                setTimeout(() => this.connectionCreationEnabled = true, 500);
            });
        };
        startConnectionSubscription(this.plottersObservables.plugInputClicked$, "input");
        startConnectionSubscription(this.plottersObservables.plugOutputClicked$, "output");
        endConnectionSubscription(this.plottersObservables.plugInputClicked$, "input");
        endConnectionSubscription(this.plottersObservables.plugOutputClicked$, "output");
        this.plottersObservables.mouseMoved$.pipe(rxjs_operators__WEBPACK_IMPORTED_MODULE_1__.filter(_ => this.drawingConnection !== undefined)).subscribe((coordinates) => this.plotDrawingConnection(this.drawingConnection, coordinates));
        this.appObservables.connectionSelected$.subscribe(c => document.getElementById(getConnectionId(c)).classList.toggle("selected"));
        this.appObservables.unselect$.subscribe(() => {
            let connection = document.getElementById("drawing-connection");
            if (connection)
                connection.remove();
            this.drawingConnection = undefined;
        });
    }
    plotDrawingConnection(drawingConnection, coordinates) {
        drawingConnection.isStarted = true;
        let coors = [(coordinates[0] - 1 - this.drawingArea.overallTranform.translateX) / this.drawingArea.overallTranform.scale,
            (coordinates[1] - 1 - this.drawingArea.overallTranform.translateY) / this.drawingArea.overallTranform.scale];
        let selection = this.drawingArea.drawingGroup.selectAll(".drawing-connection")
            .data([{
                data: drawingConnection.data,
                htmlPlug: drawingConnection.domElement
            }]);
        selection.exit().remove();
        selection.attr("x2", coors[0]);
        selection.attr("y2", coors[1]);
        selection.enter().append("line")
            .attr("id", "drawing-connection")
            .attr("class", "drawing-connection")
            .attr("x1", drawingConnection.xOrigin)
            .attr("y1", drawingConnection.yOrigin)
            .attr("x2", coors[0])
            .attr("y2", coors[1]);
    }
    connectUserInteractions(plotObservables$) {
        let click$ = plotObservables$.pipe(rxjs_operators__WEBPACK_IMPORTED_MODULE_1__.filter((d) => d.action === "click"));
        click$.subscribe((d) => this.appStore.selectConnection(d.data.data));
    }
}


/***/ }),

/***/ "./builder-editor/builder-plots/descriptions-boxes-plotter.ts":
/*!********************************************************************!*\
  !*** ./builder-editor/builder-plots/descriptions-boxes-plotter.ts ***!
  \********************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "DescriptionsBoxesPlotter": () => (/* binding */ DescriptionsBoxesPlotter)
/* harmony export */ });
/* harmony import */ var _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-svg-plots */ "@youwol/flux-svg-plots");
/* harmony import */ var _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _builder_state_index__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ../builder-state/index */ "./builder-editor/builder-state/index.ts");
/* harmony import */ var _drawing_utils__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./drawing-utils */ "./builder-editor/builder-plots/drawing-utils.ts");



function drawBoxes(descriptionsBoxes, drawingArea, appStore) {
    let plotData = descriptionsBoxes.map(box => {
        let rect = (0,_drawing_utils__WEBPACK_IMPORTED_MODULE_2__.getBoundingBox)(box.modulesId, 10, drawingArea);
        let x = drawingArea.hScale.invert(rect.x + rect.width / 2);
        let y = drawingArea.vScale.invert(rect.y + rect.height / 2);
        let selected = appStore.descriptionBoxSelected &&
            appStore.descriptionBoxSelected.descriptionBoxId == box.descriptionBoxId;
        return {
            x: x,
            y: y,
            classes: ["description-box"].concat(selected ? ["selected"] : []),
            attributes: { descriptionBoxId: box.descriptionBoxId },
            id: box.descriptionBoxId,
            data: { descriptionBox: box,
                boundingBox: rect }
        };
    });
    let plotter = new _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_0__.CrossPlot({ plotId: "descriptionsBoxPlotter",
        plotClasses: [],
        drawingArea: drawingArea,
        entities: plotData });
    plotter.defaultElementDisplay = (d) => {
        const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
        let headerHeight = 25;
        let padding = 25;
        let width = d.data.boundingBox.width;
        let height = d.data.boundingBox.height;
        g.innerHTML = `
       <rect height="${height}" width="${width}" 
        class="description-box content"  x="${-width / 2}" y="${-height / 2}"
        filter="url(#shadow)" ></rect>
        <path d="M${-width / 2},${headerHeight - padding - height / 2} v${-(headerHeight - 10)} q0,-10 10,-10 h${width - 20} q10,0 10,10  v${headerHeight - 10} z" 
                class="description-box mdle-color-fill header " />
        <path d="M${-width / 2},${headerHeight - padding - height / 2} v${-(headerHeight - 10)} q0,-10 10,-10 h${width - 20} q10,0 10,10  v${headerHeight - 10} " 
                class="description-box header outline" />

        <text class="description-box title" x="${-width / 2 + 10}" y="${-height / 2 - 5}" >${d.data.descriptionBox.title}</text>
        `;
        return g;
    };
    let drawnElements = plotter.draw(plotData);
    let format = (d) => d.filter(g => g).reduce((acc, e) => acc.concat(e), []);
    return drawnElements.entered._groups.concat(drawnElements.updated._groups).map(format).reduce((acc, e) => acc.concat(e), []);
}
class DescriptionsBoxesPlotter {
    constructor(drawingArea, plottersObservables, appObservables, appStore) {
        this.drawingArea = drawingArea;
        this.plottersObservables = plottersObservables;
        this.appObservables = appObservables;
        this.appStore = appStore;
        this.debugSingleton = _builder_state_index__WEBPACK_IMPORTED_MODULE_1__.AppDebugEnvironment.getInstance();
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowView({
                level: _builder_state_index__WEBPACK_IMPORTED_MODULE_1__.LogLevel.Info,
                message: "create descriptions boxes plotter",
                object: { drawingArea: drawingArea,
                    plottersObservables: plottersObservables }
            });
        /* This line is for ensuring that description box are plotted behind everything else :/
        *  as it ensures the svg drawing group element of description boxes is created first (at plotter creation, while other elements
        *  'wait' to be loaded or manually created)
        *  Need a better management of layer ordering
        */
        drawBoxes([], this.drawingArea, this.appStore);
        this.appObservables.descriptionsBoxesUpdated$
            .subscribe(descriptionsBoxes => {
            let svgElements = drawBoxes(descriptionsBoxes, this.drawingArea, this.appStore);
            this.connectUserInteractions(svgElements);
            this.plottersObservables.descriptionsBoxesDrawn$.next(svgElements);
        });
    }
    connectUserInteractions(svgElements) {
        svgElements.forEach((g) => g.onclick = (event) => this.appStore.selectDescriptionBox(g.id));
    }
}


/***/ }),

/***/ "./builder-editor/builder-plots/drawing-utils.ts":
/*!*******************************************************!*\
  !*** ./builder-editor/builder-plots/drawing-utils.ts ***!
  \*******************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "uuidv4": () => (/* binding */ uuidv4),
/* harmony export */   "convert": () => (/* binding */ convert),
/* harmony export */   "getBoundingBox": () => (/* binding */ getBoundingBox),
/* harmony export */   "focusElement": () => (/* binding */ focusElement),
/* harmony export */   "plugLayersTransition_noTransition": () => (/* binding */ plugLayersTransition_noTransition),
/* harmony export */   "plugLayersTransition_test": () => (/* binding */ plugLayersTransition_test)
/* harmony export */ });
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_0__);

function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}
function convert(bbox, matrix, drawingArea) {
    var offset = document.getElementById(drawingArea.svgCanvas.attr("id")).getBoundingClientRect();
    let transform = drawingArea.overallTranform;
    let a = {
        xmin: ((matrix.a * bbox.x) + (matrix.c * bbox.y) + matrix.e - offset.left
            - transform.translateX) / transform.scale,
        ymin: ((matrix.b * bbox.x) + (matrix.d * bbox.y) + matrix.f - offset.top
            - transform.translateY) / transform.scale,
        xmax: ((matrix.a * (bbox.x + bbox.width)) + (matrix.c * (bbox.y + bbox.height)) + matrix.e - offset.left
            - transform.translateX) / transform.scale,
        ymax: ((matrix.b * (bbox.x + bbox.width)) + (matrix.d * (bbox.y + bbox.height)) + matrix.f - offset.top
            - transform.translateY) / transform.scale
    };
    return a;
}
function getBoundingBox(modulesId, margin, drawingArea) {
    let bbox = modulesId
        .map((mid) => document.getElementById(mid))
        .filter(e => e)
        .map((e) => {
        /* in case the method getBBox does not exist on the svg element (e.g. during unit test - seems like
         * the proxy do not implement it), we return the x,y attributes of the <g> element (which identify to
         * the center of the graphic element)
         */
        return e.getBBox ?
            convert(e.getBBox(), e.getScreenCTM(), drawingArea) :
            { xmin: e.getAttribute("x"), xmax: e.getAttribute("x"), ymin: e.getAttribute("y"), ymax: e.getAttribute("y") };
    })
        .reduce((acc, e) => ({
        xmin: Math.min(acc.xmin, e.xmin), xmax: Math.max(acc.xmax, e.xmax),
        ymin: Math.min(acc.ymin, e.ymin), ymax: Math.max(acc.ymax, e.ymax)
    }), { xmin: 1e6, xmax: -1e6, ymin: 1e6, ymax: 1e-6 });
    return {
        x: bbox.xmin - margin,
        y: bbox.ymin - margin,
        width: bbox.xmax - bbox.xmin + 2 * margin,
        height: bbox.ymax - bbox.ymin + 2 * margin
    };
}
function focusElement(drawingArea, svgElement) {
    let boudingBox = svgElement.getBoundingClientRect();
    drawingArea.lookAt(0.5 * (boudingBox.left + boudingBox.right), 0.5 * (boudingBox.top + boudingBox.bottom));
}
function mapToFocusCoordinate(activeLayerUpdated$, appStore) {
    return activeLayerUpdated$.pipe(
    //tap( ({fromLayerId, toLayerId}) => console.log({fromLayerId, toLayerId}) ),
    (0,rxjs_operators__WEBPACK_IMPORTED_MODULE_0__.filter)(({ fromLayerId, toLayerId }) => fromLayerId != undefined && toLayerId != undefined), (0,rxjs_operators__WEBPACK_IMPORTED_MODULE_0__.map)(({ fromLayerId, toLayerId }) => ({ fromLayer: appStore.getLayer(fromLayerId), toLayer: appStore.getLayer(toLayerId) })), (0,rxjs_operators__WEBPACK_IMPORTED_MODULE_0__.map)(({ fromLayer, toLayer }) => {
        // if zoom-in
        if (fromLayer.getChildrenLayers().includes(toLayer))
            return document.getElementById("expanded_" + appStore.getGroupModule(toLayer.layerId).moduleId);
        // if zoom-out
        if (toLayer.getChildrenLayers().includes(fromLayer)) {
            let targetLayer = toLayer.children.find(layer => layer == fromLayer || layer.getChildrenLayers().includes(fromLayer));
            return document.getElementById(appStore.getGroupModule(targetLayer.layerId).moduleId);
        }
        // if zoom from/to different branches of layer tree
        return document.getElementById("expanded_" + appStore.getGroupModule(toLayer.layerId).moduleId);
    }), (0,rxjs_operators__WEBPACK_IMPORTED_MODULE_0__.map)(svgElement => {
        let boudingBox = svgElement.getBoundingClientRect();
        return [0.5 * (boudingBox.left + boudingBox.right), 0.5 * (boudingBox.top + boudingBox.bottom)];
    }));
}
function plugLayersTransition_noTransition(activeLayerUpdated$, appStore, drawingArea) {
    mapToFocusCoordinate(activeLayerUpdated$, appStore)
        .subscribe((coors) => drawingArea.lookAt(coors[0], coors[1]));
}
function plugLayersTransition_test(activeLayerUpdated$, appStore, drawingArea) {
    activeLayerUpdated$.subscribe(() => drawingArea.selectAll("g.connection").remove());
    mapToFocusCoordinate(activeLayerUpdated$, appStore)
        .subscribe((coors) => {
        let zoom = drawingArea.zoom;
        drawingArea.svgCanvas.transition()
            .duration(1000)
            .call(zoom.translateTo, coors[0], coors[1]);
    });
}


/***/ }),

/***/ "./builder-editor/builder-plots/extension.ts":
/*!***************************************************!*\
  !*** ./builder-editor/builder-plots/extension.ts ***!
  \***************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "BuilderRenderingAPI": () => (/* binding */ BuilderRenderingAPI)
/* harmony export */ });
class BuilderRenderingAPI {
    static initialize(wfPlotter) {
        BuilderRenderingAPI.workflowPlotter = wfPlotter;
    }
}


/***/ }),

/***/ "./builder-editor/builder-plots/index.ts":
/*!***********************************************!*\
  !*** ./builder-editor/builder-plots/index.ts ***!
  \***********************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "WorkflowPlotter": () => (/* reexport safe */ _workflow_plotter__WEBPACK_IMPORTED_MODULE_0__.WorkflowPlotter),
/* harmony export */   "ModulesPlotter": () => (/* reexport safe */ _modules_plotter__WEBPACK_IMPORTED_MODULE_1__.ModulesPlotter),
/* harmony export */   "createPlot": () => (/* reexport safe */ _modules_plotter__WEBPACK_IMPORTED_MODULE_1__.createPlot),
/* harmony export */   "BoxSelectorPlotter": () => (/* reexport safe */ _box_selector_plotter__WEBPACK_IMPORTED_MODULE_2__.BoxSelectorPlotter),
/* harmony export */   "ConnectionsPlotter": () => (/* reexport safe */ _connections_plotter__WEBPACK_IMPORTED_MODULE_3__.ConnectionsPlotter),
/* harmony export */   "DescriptionsBoxesPlotter": () => (/* reexport safe */ _descriptions_boxes_plotter__WEBPACK_IMPORTED_MODULE_4__.DescriptionsBoxesPlotter)
/* harmony export */ });
/* harmony import */ var _workflow_plotter__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./workflow-plotter */ "./builder-editor/builder-plots/workflow-plotter.ts");
/* harmony import */ var _modules_plotter__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./modules-plotter */ "./builder-editor/builder-plots/modules-plotter.ts");
/* harmony import */ var _box_selector_plotter__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./box-selector-plotter */ "./builder-editor/builder-plots/box-selector-plotter.ts");
/* harmony import */ var _connections_plotter__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./connections-plotter */ "./builder-editor/builder-plots/connections-plotter.ts");
/* harmony import */ var _descriptions_boxes_plotter__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./descriptions-boxes-plotter */ "./builder-editor/builder-plots/descriptions-boxes-plotter.ts");







/***/ }),

/***/ "./builder-editor/builder-plots/models-view.ts":
/*!*****************************************************!*\
  !*** ./builder-editor/builder-plots/models-view.ts ***!
  \*****************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "PlotterEntity": () => (/* binding */ PlotterEntity),
/* harmony export */   "PlotterConnectionEntity": () => (/* binding */ PlotterConnectionEntity)
/* harmony export */ });
class PlotterEntity {
    constructor(id, classes, data) {
        this.id = id;
        this.classes = classes;
        this.data = data;
    }
}
class PlotterConnectionEntity extends PlotterEntity {
    constructor(id, classes, inputGroup, outputGroup, data, adaptor = undefined) {
        super(id, classes, data);
        this.id = id;
        this.classes = classes;
        this.inputGroup = inputGroup;
        this.outputGroup = outputGroup;
        this.data = data;
        this.adaptor = adaptor;
    }
}


/***/ }),

/***/ "./builder-editor/builder-plots/modules-plotter.ts":
/*!*********************************************************!*\
  !*** ./builder-editor/builder-plots/modules-plotter.ts ***!
  \*********************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "createPlot": () => (/* binding */ createPlot),
/* harmony export */   "ModulesPlotter": () => (/* binding */ ModulesPlotter)
/* harmony export */ });
/* harmony import */ var lodash__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! lodash */ "lodash");
/* harmony import */ var lodash__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(lodash__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var d3_drag__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! d3-drag */ "../../node_modules/d3-drag/src/drag.js");
/* harmony import */ var d3_selection__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(/*! d3-selection */ "../../node_modules/d3-selection/src/select.js");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! @youwol/flux-svg-plots */ "@youwol/flux-svg-plots");
/* harmony import */ var _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3__);
/* harmony import */ var _builder_state_index__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ../builder-state/index */ "./builder-editor/builder-state/index.ts");
/* harmony import */ var _plugins_plotter__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./plugins-plotter */ "./builder-editor/builder-plots/plugins-plotter.ts");
/* harmony import */ var _drawing_utils__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! ./drawing-utils */ "./builder-editor/builder-plots/drawing-utils.ts");









/** Temporary until migration is complete
 *
 * @param mdle
 * @param drawingArea
 */
function createPlot(mdle, drawingArea) {
    let Factory = mdle.Factory;
    let Rendering = new Factory.BuilderView();
    let entities$ = new rxjs__WEBPACK_IMPORTED_MODULE_1__.Subject();
    let plotId = (0,_youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3__.toCssName)(Factory.uid) + "_ModulesPlot";
    let plotter = new _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3__.CrossPlot({
        plotId: plotId,
        plotClasses: [plotId, Factory.packId], drawingArea,
        entities$
    });
    plotter.defaultElementDisplay = (d) => Rendering.render(d.data.module);
    return plotter;
}
function getCenter(currentViews) {
    let views = currentViews.modulesView;
    let coorsParentLayer = views.map(m => [m.xWorld, m.yWorld]);
    let xmin = coorsParentLayer.reduce((acc, e) => acc < e[0] ? acc : e[0], 1.e10);
    let xmax = coorsParentLayer.reduce((acc, e) => acc > e[0] ? acc : e[0], -1.e10);
    let ymin = coorsParentLayer.reduce((acc, e) => acc < e[1] ? acc : e[1], 1.e10);
    let ymax = coorsParentLayer.reduce((acc, e) => acc > e[1] ? acc : e[1], -1.e10);
    return [(xmax + xmin) / 2, (ymax + ymin) / 2];
}
function getScaleFactors(currentViews) {
    let views = currentViews.modulesView;
    let coorsParentLayer = views.map(m => [m.xWorld, m.yWorld]);
    let xmin = coorsParentLayer.reduce((acc, e) => acc < e[0] ? acc : e[0], 1.e10);
    let xmax = coorsParentLayer.reduce((acc, e) => acc > e[0] ? acc : e[0], -1.e10);
    let ymin = coorsParentLayer.reduce((acc, e) => acc < e[1] ? acc : e[1], 1.e10);
    let ymax = coorsParentLayer.reduce((acc, e) => acc > e[1] ? acc : e[1], -1.e10);
    return [(xmax - xmin) / 2, (ymax - ymin) / 2];
}
function drawModules(drawingArea, appStore, plotObservables$) {
    let allPlots = [];
    let displayedModulesView = appStore.getDisplayedModulesView();
    let projection = undefined;
    if (appStore.activeLayerId != appStore.project.workflow.rootLayerTree.layerId) {
        let center = getCenter(displayedModulesView.currentLayer);
        let factors = getScaleFactors(displayedModulesView.currentLayer);
        let moduleViewLayer = displayedModulesView.parentLayer.currentGroupModuleView;
        projection = (x, y) => {
            let d0 = Math.pow((x - moduleViewLayer.xWorld) * (x - moduleViewLayer.xWorld) + (y - moduleViewLayer.yWorld) * (y - moduleViewLayer.yWorld), 0.5);
            let cos_theta0 = (x - moduleViewLayer.xWorld) / d0;
            let sin_theta0 = (y - moduleViewLayer.yWorld) / d0;
            let dx = (d0 + factors[0]) * cos_theta0 + cos_theta0 / Math.abs(cos_theta0) * 50;
            let dy = (d0 + factors[1]) * sin_theta0 + sin_theta0 / Math.abs(sin_theta0) * 75;
            return [center[0] + dx, center[1] + dy];
        };
    }
    let fromModuleViewInside = (view) => ({
        x: view.xWorld,
        y: view.yWorld,
        classes: ["module"].concat(appStore.isSelected(view.moduleId) ? ["selected"] : []),
        attributes: { moduleId: view.moduleId },
        id: view.moduleId,
        Factory: view.Factory,
        data: { module: appStore.getModule(view.moduleId),
            moduleView: view }
    });
    let fromModuleOutside = (view) => Object.assign({}, fromModuleViewInside(view), { projection: projection });
    let plotsData0 = displayedModulesView.currentLayer.modulesView.map(fromModuleViewInside);
    let plotsData1 = displayedModulesView.parentLayer.modulesView.map(fromModuleOutside);
    let grouped = lodash__WEBPACK_IMPORTED_MODULE_0__.groupBy([...plotsData0, ...plotsData1], d => d.Factory.uid);
    let modulesDrawn = {};
    let activeSeriesId = [];
    let updateMdlesDrawn = (d) => {
        d.filter(g => g).forEach(g => {
            if (g.id.includes("group")) {
                let m = appStore.getModule(g.id);
                let mIds = m.inputSlots.map(s => s.moduleId).concat(m.outputSlots.map(s => s.moduleId));
                mIds.forEach(mid => { modulesDrawn[mid] = g; });
            }
            modulesDrawn[g.id] = g;
        });
    };
    Object.entries(grouped).map(([factId, modules]) => {
        let plot = createPlot(modules[0], drawingArea);
        activeSeriesId.push(plot.plotId);
        allPlots.push(plot);
        let groups = plot.draw(modules);
        groups.entered._groups.forEach(d => updateMdlesDrawn(d));
        groups.updated._groups.forEach(d => updateMdlesDrawn(d));
        plot.entities$.subscribe(d => plotObservables$.next(d));
        return plot;
    });
    return { modulesDrawn: modulesDrawn,
        activeSeries: activeSeriesId };
}
function drawExpandedGroup(layerId, drawingArea, appStore) {
    if (!layerId || layerId === appStore.project.workflow.rootLayerTree.layerId) {
        let plotter = new _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3__.CrossPlot({ plotId: "activeLayerPlotter", plotClasses: [], drawingArea, entities: [] });
        plotter.draw([]);
        return {};
    }
    let activateLayer = appStore.getLayer(layerId);
    let groupMdle = appStore.project.workflow.modules
        .find(m => m instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.GroupModules.Module && m.layerId == activateLayer.layerId);
    const displayedElements = appStore.getDisplayedModulesView();
    const includedEntities = displayedElements.currentLayer.modulesView.map(g => g.moduleId);
    let rect = (0,_drawing_utils__WEBPACK_IMPORTED_MODULE_6__.getBoundingBox)(includedEntities, 50, drawingArea);
    let x = drawingArea.hScale.invert(rect.x + rect.width / 2);
    let y = drawingArea.vScale.invert(rect.y + rect.height / 2);
    let plotData = [{
            id: "expanded_" + groupMdle.moduleId,
            x: x, y: y,
            classes: ["active-layer-box"],
            attributes: { layerId: layerId },
            data: { boundingBox: rect }
        }];
    let plotter = new _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3__.CrossPlot({ plotId: "activeLayerPlotter", plotClasses: [],
        drawingArea: drawingArea, entities: plotData });
    plotter.defaultElementDisplay = _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.GroupModules.expandedGroupPlot(groupMdle);
    let drawnElements = plotter.draw(plotData);
    let all = drawnElements.entered._groups.concat(drawnElements.updated._groups).reduce((acc, e) => acc.concat(e), []).filter(g => g);
    return { [groupMdle.moduleId]: all[0] };
}
class ModulesPlotter {
    constructor(drawingArea, plottersObservables, appObservables, appStore) {
        this.drawingArea = drawingArea;
        this.plottersObservables = plottersObservables;
        this.appObservables = appObservables;
        this.appStore = appStore;
        this.plotsFactory = {};
        this.debugSingleton = _builder_state_index__WEBPACK_IMPORTED_MODULE_4__.AppDebugEnvironment.getInstance();
        this.modulePlots = [];
        this.previousActiveSeriesId = [];
        this.dragging = false;
        this.dragTranslation = [0, 0];
        let plotObservables$ = new rxjs__WEBPACK_IMPORTED_MODULE_1__.Subject();
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowView({
                level: _builder_state_index__WEBPACK_IMPORTED_MODULE_4__.LogLevel.Info,
                message: "create modules plotter",
                object: { drawingArea: drawingArea,
                    plottersObservables: plottersObservables }
            });
        // This line is for ensuring that the active layer is plotted behind everything else :/
        (new _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3__.CrossPlot({ plotId: "activeLayerPlotter", plotClasses: [], drawingArea: drawingArea, entities: [] })).draw([]);
        this.pluginsPlotter = new _plugins_plotter__WEBPACK_IMPORTED_MODULE_5__.PluginsPlotter(this.drawingArea, this.plottersObservables, this.appObservables, this.appStore);
        (0,rxjs__WEBPACK_IMPORTED_MODULE_1__.combineLatest)([appObservables.packagesLoaded$, this.plottersObservables.modulesViewUpdated$])
            .subscribe(() => {
            let { modulesDrawn, activeSeries } = drawModules(this.drawingArea, this.appStore, plotObservables$);
            let pluginsDrawn = this.pluginsPlotter.draw(modulesDrawn);
            let expandedGroup = drawExpandedGroup(this.appStore.activeLayerId, this.drawingArea, this.appStore);
            this.connectUserInteractions(Object.assign({}, modulesDrawn, expandedGroup));
            this.emptyRemovedSeries(this.previousActiveSeriesId, activeSeries);
            this.previousActiveSeriesId = activeSeries;
            this.plottersObservables.modulesDrawn$.next({ ...modulesDrawn, ...pluginsDrawn, ...expandedGroup });
        });
        this.appObservables.moduleSelected$.subscribe(mdle => {
            let elem = document.getElementById(mdle.moduleId);
            if (elem && !elem.classList.contains("selected"))
                elem.classList.add("selected");
        });
        this.appObservables.modulesUnselected$.subscribe(mdles => {
            mdles.forEach(mdle => {
                let elem = document.getElementById(mdle.moduleId);
                if (elem && elem.classList.contains("selected"))
                    elem.classList.remove("selected");
            });
        });
        appObservables.unselect$.subscribe(() => {
            this.unselect();
        });
    }
    highlight(modulesId) {
        let htmlElems = modulesId
            .map((mid) => document.getElementById(mid));
        htmlElems.forEach(e => { if (e)
            e.classList.add("highlighted"); });
    }
    unselect() {
        let htmlElems = document.getElementsByClassName("selected");
        while (htmlElems.length > 0) {
            htmlElems[0].classList.remove("selected");
            htmlElems = document.getElementsByClassName("selected");
        }
        htmlElems = document.getElementsByClassName("highlighted");
        while (htmlElems.length > 0) {
            htmlElems[0].classList.remove("highlighted");
            htmlElems = document.getElementsByClassName("highlighted");
        }
    }
    connectUserInteractions(modulesDrawn) {
        Object.entries(modulesDrawn).forEach(([moduleId, g]) => {
            let onclick = (event) => {
                if (event.target.classList.contains("slot")) {
                    event.target.classList.contains("output") ?
                        this.plottersObservables.plugOutputClicked$.next({ event, group: g, moduleId }) :
                        this.plottersObservables.plugInputClicked$.next({ event, group: g, moduleId });
                    return;
                }
                event.stopPropagation();
                this.appStore.selectModule(moduleId);
            };
            g.onclick = onclick;
            g.onmousedown = onclick;
            if (this.appStore.project.workflow.plugins.map(m => m.moduleId).includes(moduleId))
                return;
            if (g.classList.contains("active-layer-box"))
                return;
            var drag = (0,d3_drag__WEBPACK_IMPORTED_MODULE_7__.default)();
            drag
                .on("start", (ev) => {
                this.dragSelection(ev, false);
            })
                .on("drag", (ev) => this.dragSelection(ev, false))
                .on("end", (ev) => this.dragSelection(ev, true));
            (0,d3_selection__WEBPACK_IMPORTED_MODULE_8__.default)(g).call(drag);
        });
    }
    emptyRemovedSeries(oldSeries, newSeries) {
        let removeds = oldSeries.filter(name => !newSeries.includes(name));
        removeds.forEach(name => document.querySelector("g#" + name).remove());
    }
    dragSelection(d3Event, update) {
        this.dragging = true;
        let modules = this.appStore
            .getModulesSelected()
            .filter(m => this.appStore.getActiveLayer().moduleIds.includes(m.moduleId) || m["layerId"]);
        let newPos = [];
        modules.forEach(m => {
            let g = document.getElementById(m.moduleId);
            let plugins = g.querySelectorAll('g.plugin');
            let x = Number(g.getAttribute("x")) + d3Event.dx;
            let y = Number(g.getAttribute("y")) + d3Event.dy;
            Array.from(plugins).forEach(gPlugin => {
                gPlugin.setAttribute("x", Number(gPlugin.getAttribute("x")) + d3Event.dx);
                gPlugin.setAttribute("y", Number(gPlugin.getAttribute("y")) + d3Event.dy);
            });
            this.dragTranslation[0] += d3Event.dx;
            this.dragTranslation[1] -= d3Event.dy;
            g.setAttribute("x", x);
            g.setAttribute("y", y);
            g.style.transform = "translate(" + x + "px," + y + "px)";
            g.setAttribute("transform", "translate(" + x + "," + y + ")");
            if (update) {
                newPos.push({
                    moduleId: m.moduleId,
                    x: this.drawingArea.hScale.invert(x),
                    y: this.drawingArea.vScale.invert(y),
                    translation: this.dragTranslation
                });
                g.style.transform = "";
            }
        });
        if (update) {
            this.appStore.moveModules(newPos);
            this.dragging = false;
            this.dragTranslation = [0, 0];
        }
        return newPos;
    }
}


/***/ }),

/***/ "./builder-editor/builder-plots/plugins-plotter.ts":
/*!*********************************************************!*\
  !*** ./builder-editor/builder-plots/plugins-plotter.ts ***!
  \*********************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "PluginsPlotter": () => (/* binding */ PluginsPlotter)
/* harmony export */ });
/* harmony import */ var _builder_state_index__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../builder-state/index */ "./builder-editor/builder-state/index.ts");

function drawPlugin(plugin, containerGroup, appStore) {
    let display = new plugin.Factory.BuilderView();
    let pluginGroup = display.render(plugin);
    pluginGroup.onclick = (e) => { e.stopPropagation(); appStore.selectModule(plugin.moduleId); };
    let a = containerGroup.querySelector("#" + plugin.moduleId);
    if (a)
        a.remove();
    pluginGroup.id = plugin.moduleId;
    pluginGroup.classList.add("module", "plugin");
    let dyModule = 0;
    let dyPlugin = 50;
    if (containerGroup.getBBox)
        dyModule = containerGroup.getBBox().height - containerGroup.querySelector(".content").getBBox().height / 2;
    // we need to actually append the group of the plugin to get its bounding box
    containerGroup.appendChild(pluginGroup);
    if (pluginGroup.getBBox)
        dyPlugin = pluginGroup.getBBox().height / 2;
    let dy = dyModule + dyPlugin;
    pluginGroup.setAttribute("x", containerGroup.getAttribute("x"));
    pluginGroup.setAttribute("y", Number(containerGroup.getAttribute("y")) + dy);
    pluginGroup.setAttribute("transform", "translate(0," + dy + ")");
    return pluginGroup;
}
class PluginsPlotter {
    constructor(drawingArea, plottersObservables, appObservables, appStore) {
        this.drawingArea = drawingArea;
        this.plottersObservables = plottersObservables;
        this.appObservables = appObservables;
        this.appStore = appStore;
        this.debugSingleton = _builder_state_index__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
        this.groups = {};
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowView({
                level: _builder_state_index__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
                message: "create plugins plotter",
                object: { drawingArea, plottersObservables }
            });
    }
    draw(modulesDrawn) {
        Object.values(this.groups).forEach((g) => g.remove());
        let plugInsToPlot = this.appStore.project.workflow.plugins
            .filter(p => modulesDrawn[p.parentModule.moduleId])
            .map(p => [p, modulesDrawn[p.parentModule.moduleId]]);
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowView({
                level: _builder_state_index__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
                message: "PluginsPlotter draw",
                object: { modulesDrawn: modulesDrawn, plugins: this.appStore.project.workflow.plugins, plugInsToPlot }
            });
        this.groups = plugInsToPlot
            .map(([plugin, parentSvgGroup]) => [plugin.moduleId, drawPlugin(plugin, parentSvgGroup, this.appStore)])
            .reduce((acc, e) => { acc[e[0]] = e[1]; return acc; }, {});
        return this.groups;
    }
}


/***/ }),

/***/ "./builder-editor/builder-plots/workflow-plotter.ts":
/*!**********************************************************!*\
  !*** ./builder-editor/builder-plots/workflow-plotter.ts ***!
  \**********************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "WorkflowPlotter": () => (/* binding */ WorkflowPlotter)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _builder_state_index__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ../builder-state/index */ "./builder-editor/builder-state/index.ts");
/* harmony import */ var _connections_plotter__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./connections-plotter */ "./builder-editor/builder-plots/connections-plotter.ts");
/* harmony import */ var _modules_plotter__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./modules-plotter */ "./builder-editor/builder-plots/modules-plotter.ts");
/* harmony import */ var _box_selector_plotter__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./box-selector-plotter */ "./builder-editor/builder-plots/box-selector-plotter.ts");
/* harmony import */ var _descriptions_boxes_plotter__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./descriptions-boxes-plotter */ "./builder-editor/builder-plots/descriptions-boxes-plotter.ts");
/* harmony import */ var _drawing_utils__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! ./drawing-utils */ "./builder-editor/builder-plots/drawing-utils.ts");
/* harmony import */ var _extension__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! ./extension */ "./builder-editor/builder-plots/extension.ts");








class WorkflowPlotter {
    constructor(drawingArea, appObservables, plottersObservables, appStore, options = { margin: 50 }) {
        this.drawingArea = drawingArea;
        this.appObservables = appObservables;
        this.plottersObservables = plottersObservables;
        this.appStore = appStore;
        this.options = options;
        this.debugSingleton = _builder_state_index__WEBPACK_IMPORTED_MODULE_1__.AppDebugEnvironment.getInstance();
        this.modulesPlotter = undefined;
        this.connectionsPlotters = undefined;
        this.boxSelectorPlotter = undefined;
        this.descriptionsBoxesPlotter = undefined;
        this.pluginsPlotter = undefined;
        this.descriptionsBoxesPlotter = new _descriptions_boxes_plotter__WEBPACK_IMPORTED_MODULE_5__.DescriptionsBoxesPlotter(this.drawingArea, this.plottersObservables, this.appObservables, this.appStore);
        this.modulesPlotter = new _modules_plotter__WEBPACK_IMPORTED_MODULE_3__.ModulesPlotter(this.drawingArea, this.plottersObservables, this.appObservables, this.appStore);
        this.connectionsPlotters = new _connections_plotter__WEBPACK_IMPORTED_MODULE_2__.ConnectionsPlotter(this.drawingArea, this.plottersObservables, this.appObservables, this.appStore);
        this.boxSelectorPlotter = new _box_selector_plotter__WEBPACK_IMPORTED_MODULE_4__.BoxSelectorPlotter(this.drawingArea, this.plottersObservables, this.appObservables, this.appStore, this.modulesPlotter);
        (0,_drawing_utils__WEBPACK_IMPORTED_MODULE_6__.plugLayersTransition_noTransition)(this.appObservables.activeLayerUpdated$, this.appStore, this.drawingArea);
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowView({
                level: _builder_state_index__WEBPACK_IMPORTED_MODULE_1__.LogLevel.Info,
                message: "create WorkflowPlotter",
                object: {
                    drawingArea: this.drawingArea,
                    modulePlotter: this.modulesPlotter,
                    connectionsPlotters: this.connectionsPlotters
                }
            });
        let plotObservable = this.plottersObservables;
        let boxSelectorPlotter = this.boxSelectorPlotter;
        let background = document.querySelector("svg");
        let toPosition = (event) => [event.offsetX || event.clientX, event.offsetY || event.clientY];
        background.onmousedown = (event) => {
            boxSelectorPlotter.startSelection(toPosition(event));
        };
        background.onmousemove = (event) => {
            if (event.ctrlKey)
                boxSelectorPlotter.moveTo(toPosition(event));
            else
                plotObservable.mouseMoved$.next(toPosition(event));
        };
        background.onmouseup = (event) => {
            if (event.ctrlKey)
                boxSelectorPlotter.finishSelection(toPosition(event));
        };
        background.onclick = (event) => {
            if (!event.ctrlKey)
                appStore.unselect();
        };
        window.onkeydown = (event) => {
            if (event.key == "Delete" && document.activeElement.tagName == "BODY")
                this.appStore.deleteSelected();
        };
        this.loadExtensions();
    }
    loadExtensions() {
        // this test is for backward compatibility w/ flux-lib-core
        if (!_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.FluxExtensionAPIs)
            return;
        _extension__WEBPACK_IMPORTED_MODULE_7__.BuilderRenderingAPI.initialize(this);
        _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.FluxExtensionAPIs.registerAPI('BuilderRenderingAPI', _extension__WEBPACK_IMPORTED_MODULE_7__.BuilderRenderingAPI);
    }
}


/***/ }),

/***/ "./builder-editor/builder-state/app-debug.environment.ts":
/*!***************************************************************!*\
  !*** ./builder-editor/builder-state/app-debug.environment.ts ***!
  \***************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "LogLevel": () => (/* binding */ LogLevel),
/* harmony export */   "LogEntry": () => (/* binding */ LogEntry),
/* harmony export */   "LogerConsole": () => (/* binding */ LogerConsole),
/* harmony export */   "AppDebugEnvironment": () => (/* binding */ AppDebugEnvironment)
/* harmony export */ });
var LogLevel;
(function (LogLevel) {
    LogLevel[LogLevel["Debug"] = 0] = "Debug";
    LogLevel[LogLevel["Info"] = 1] = "Info";
    LogLevel[LogLevel["Error"] = 2] = "Error";
})(LogLevel || (LogLevel = {}));
class LogEntry {
    constructor(topic, message, object, level) {
        this.topic = topic;
        this.message = message;
        this.object = object;
        this.level = level;
        this.hours = 0;
        this.minutes = 0;
        this.seconds = 0;
        this.miniseconds = 0;
        this.date = new Date();
    }
}
class LogerConsole {
    log(e) {
        if (e.level == LogLevel.Info || e.level == LogLevel.Debug)
            console.log("#" + e.topic, { date: e.date.getHours() + "h" + e.date.getMinutes() + "mn" + e.date.getSeconds() + "s" + e.date.getMilliseconds(),
                level: e.level,
                message: e.message,
                object: e.object
            });
        if (e.level == LogLevel.Error)
            console.error("#" + e.topic, { date: e.date.getHours() + "h" + e.date.getMinutes() + "mn" + e.date.getSeconds() + "s" + e.date.getMilliseconds(),
                level: e.level,
                message: e.message,
                object: e.object
            });
    }
}
class AppDebugEnvironment {
    constructor({ WorkflowBuilder, workflowView, observable, UI, renderTopicLevel }) {
        this.debugOn = true;
        this.WorkflowBuilderEnabled = true;
        this.WorkflowBuilderLevel = LogLevel.Info;
        this.workflowViewEnabled = true;
        this.workflowViewLevel = LogLevel.Info;
        this.workflowView$Enabled = true;
        this.workflowView$Level = LogLevel.Info;
        this.observableEnabled = true;
        this.observableLevel = LogLevel.Info;
        this.renderTopicEnabled = true;
        this.renderTopicLevel = LogLevel.Info;
        this.appTopicEnabled = true;
        this.appTopicLevel = LogLevel.Info;
        this.workflowUIEnabled = true;
        this.loger = new LogerConsole();
        this.WorkflowBuilderLevel = WorkflowBuilder;
        this.observableLevel = observable;
        this.renderTopicLevel = renderTopicLevel;
    }
    logWorkflowBuilder({ level, message, object }) {
        this.WorkflowBuilderEnabled &&
            level >= this.WorkflowBuilderLevel &&
            this.loger.log(new LogEntry("WorkflowBuilder", message, object, level));
    }
    logObservable({ level, message, object }) {
        this.observableEnabled &&
            level >= this.observableLevel &&
            this.loger.log(new LogEntry("Observables", message, object, level));
    }
    logWorkflowView({ level, message, object }) {
        this.workflowViewEnabled &&
            level >= this.workflowViewLevel &&
            this.loger.log(new LogEntry("WorkflowView", message, object, level));
    }
    logWorkflowView$({ level, message, object }) {
        this.workflowView$Enabled &&
            level >= this.workflowView$Level &&
            this.loger.log(new LogEntry("WorkflowView Observables", message, object, level));
    }
    logRenderTopic({ level, message, object }) {
        this.renderTopicEnabled &&
            level >= this.renderTopicLevel &&
            this.loger.log(new LogEntry("Render", message, object, level));
    }
    logAppTopic({ level, message, object }) {
        this.appTopicEnabled &&
            level >= this.appTopicLevel &&
            this.loger.log(new LogEntry("App", message, object, level));
    }
    static getInstance() {
        if (!AppDebugEnvironment.instance)
            AppDebugEnvironment.instance = new AppDebugEnvironment({ WorkflowBuilder: LogLevel.Info,
                workflowView: LogLevel.Info,
                UI: LogLevel.Info,
                observable: LogLevel.Info,
                renderTopicLevel: LogLevel.Info,
                appTopicLevel: LogLevel.Info
            });
        return AppDebugEnvironment.instance;
    }
}
AppDebugEnvironment.instance = undefined;


/***/ }),

/***/ "./builder-editor/builder-state/app-extensions-observables.service.ts":
/*!****************************************************************************!*\
  !*** ./builder-editor/builder-state/app-extensions-observables.service.ts ***!
  \****************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "AppExtensionsObservables": () => (/* binding */ AppExtensionsObservables)
/* harmony export */ });
/* harmony import */ var _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./app-debug.environment */ "./builder-editor/builder-state/app-debug.environment.ts");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__);


class AppExtensionsObservables extends _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.ExtensionsObservables {
    constructor() {
        super();
        this.debugSingleton = _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
        if (this.debugSingleton.debugOn) {
            ["projectUpdated$"]
                .forEach(id => this[id].subscribe((...args) => this.log(id, ...args)));
        }
    }
    static getInstance() {
        if (!AppExtensionsObservables.instance)
            AppExtensionsObservables.instance = new AppExtensionsObservables();
        return AppExtensionsObservables.instance;
    }
    log(name, ...args) {
        this.debugSingleton.debugOn &&
            this.debugSingleton.logObservable({
                level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
                message: name,
                object: { args: args
                }
            });
    }
}
AppExtensionsObservables.instance = undefined;


/***/ }),

/***/ "./builder-editor/builder-state/app-observables.service.ts":
/*!*****************************************************************!*\
  !*** ./builder-editor/builder-state/app-observables.service.ts ***!
  \*****************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "AppObservables": () => (/* binding */ AppObservables)
/* harmony export */ });
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./app-debug.environment */ "./builder-editor/builder-state/app-debug.environment.ts");


class AppObservables {
    constructor() {
        this.debugSingleton = _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__.AppDebugEnvironment.getInstance();
        this.packagesObserver$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.ReplaySubject(1);
        this.packagesLoaded$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.ReplaySubject(1);
        this.uiStateUpdated$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.ReplaySubject(1);
        this.packagesUpdated$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.connectionsUpdated$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.modulesUpdated$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.moduleAdded$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.moduleSelected$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.modulesUnselected$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.moduleSettingsEdited$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.adaptorEdited$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.connectionSelected$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.unselect$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.renderingLoaded$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.cssUpdated$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.descriptionsBoxesUpdated$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.activeLayerUpdated$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.ready$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.ReplaySubject(1);
        this.flowReady$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.suggestions$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.notifications$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        if (this.debugSingleton.debugOn) {
            ["packagesObserver$", "packagesLoaded$", "packagesUpdated$", "connectionsUpdated$",
                "unselect$", "moduleSelected$", "modulesUnselected$", "moduleSettingsEdited$", "connectionSelected$",
                "renderingLoaded$", "moduleAdded$", "cssUpdated$", "uiStateUpdated$", "descriptionsBoxesUpdated$",
                "activeLayerUpdated$", "ready$", "flowReady$", "suggestions$", "modulesUpdated$", "notifications$"]
                .forEach(id => this[id].subscribe((...args) => this.log(id, ...args)));
        }
    }
    static getInstance() {
        if (!AppObservables.instance)
            AppObservables.instance = new AppObservables();
        return AppObservables.instance;
    }
    log(name, ...args) {
        this.debugSingleton.debugOn &&
            this.debugSingleton.logObservable({
                level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__.LogLevel.Info,
                message: name,
                object: { args: args
                }
            });
    }
}
AppObservables.instance = undefined;


/***/ }),

/***/ "./builder-editor/builder-state/app-store-connections.ts":
/*!***************************************************************!*\
  !*** ./builder-editor/builder-state/app-store-connections.ts ***!
  \***************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "subscribeConnections": () => (/* binding */ subscribeConnections),
/* harmony export */   "addConnection": () => (/* binding */ addConnection),
/* harmony export */   "addAdaptor": () => (/* binding */ addAdaptor),
/* harmony export */   "updateAdaptor": () => (/* binding */ updateAdaptor),
/* harmony export */   "deleteAdaptor": () => (/* binding */ deleteAdaptor),
/* harmony export */   "deleteConnection": () => (/* binding */ deleteConnection),
/* harmony export */   "setConnectionView": () => (/* binding */ setConnectionView)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./app-debug.environment */ "./builder-editor/builder-state/app-debug.environment.ts");
/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./utils */ "./builder-editor/builder-state/utils.ts");



function subscribeConnections(allSubscriptions, delta, modules, plugins) {
    let flatInputSlots = modules.concat(plugins).reduce((acc, e) => acc.concat(e.inputSlots), []);
    let flatOutputSlots = modules.concat(plugins).reduce((acc, e) => acc.concat(e.outputSlots), []);
    delta.removedElements.forEach((c) => {
        allSubscriptions.get(c).unsubscribe();
        allSubscriptions.delete(c);
    });
    delta.createdElements.forEach((c) => {
        let slotOut = flatOutputSlots.find(slot => slot.slotId == c.start.slotId && slot.moduleId == c.start.moduleId);
        let slotIn = flatInputSlots.find(slot => slot.slotId == c.end.slotId && slot.moduleId == c.end.moduleId);
        let subscription = slotOut.observable$.subscribe(d => slotIn.subscribeFct({ connection: c, message: d }));
        allSubscriptions.set(c, subscription);
    });
}
function addConnection(connection, project, allSubscriptions) {
    let debugSingleton = _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__.AppDebugEnvironment.getInstance();
    debugSingleton.debugOn &&
        debugSingleton.logWorkflowBuilder({
            level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__.LogLevel.Info,
            message: "connection added",
            object: { connection: connection
            }
        });
    let modules = project.workflow.modules;
    let connections = project.workflow.connections.concat(connection);
    let workflow = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Workflow(modules, connections, project.workflow.plugins, project.workflow.rootLayerTree);
    workflow = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Workflow(modules, connections, project.workflow.plugins, project.workflow.rootLayerTree);
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project(project.name, project.description, project.requirements, workflow, project.builderRendering, project.runnerRendering);
    return projectNew;
}
function addAdaptor(connection, adaptor, project, allSubscriptions) {
    let connections = project.workflow.connections.filter(c => c != connection);
    let newConnection = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Connection(connection.start, connection.end, adaptor);
    let workflow = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Workflow(project.workflow.modules, connections.concat(newConnection), project.workflow.plugins, project.workflow.rootLayerTree);
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project(project.name, project.description, project.requirements, workflow, project.builderRendering, project.runnerRendering);
    return projectNew;
}
function updateAdaptor(connection, mappingFunction, project, allSubscriptions) {
    let connections = project.workflow.connections.filter(c => c !== connection);
    let adaptor = connection.adaptor
        ? new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Adaptor(connection.adaptor.adaptorId, mappingFunction)
        : new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Adaptor((0,_utils__WEBPACK_IMPORTED_MODULE_2__.uuidv4)(), mappingFunction);
    let newConnection = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Connection(connection.start, connection.end, adaptor);
    let workflow = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Workflow(project.workflow.modules, connections.concat(newConnection), project.workflow.plugins, project.workflow.rootLayerTree);
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project(project.name, project.description, project.requirements, workflow, project.builderRendering, project.runnerRendering);
    return projectNew;
}
function deleteAdaptor(connection, project, allSubscriptions) {
    let connections = project.workflow.connections.filter(c => c != connection);
    let newConnection = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Connection(connection.start, connection.end, undefined);
    let workflow = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Workflow(project.workflow.modules, connections.concat(newConnection), project.workflow.plugins, project.workflow.rootLayerTree);
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project(project.name, project.description, project.requirements, workflow, project.builderRendering, project.runnerRendering);
    return projectNew;
}
function deleteConnection(connection, project, allSubscriptions) {
    let connections = project.workflow.connections.filter(c => c != connection);
    let workflow = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Workflow(project.workflow.modules, connections, project.workflow.plugins, project.workflow.rootLayerTree);
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project(project.name, project.description, project.requirements, workflow, project.builderRendering, project.runnerRendering);
    return projectNew;
}
function setConnectionView(connection, config, project) {
    let connectViews = project.builderRendering.connectionsView
        .filter(c => c.connectionId != connection.connectionId)
        .concat([{ connectionId: connection.connectionId, wireless: config.wireless }]);
    let builderRendering = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.BuilderRendering(project.builderRendering.modulesView, connectViews, project.builderRendering.descriptionsBoxes);
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project(project.name, project.description, project.requirements, project.workflow, builderRendering, project.runnerRendering);
    return projectNew;
}


/***/ }),

/***/ "./builder-editor/builder-state/app-store-dependencies.ts":
/*!****************************************************************!*\
  !*** ./builder-editor/builder-state/app-store-dependencies.ts ***!
  \****************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "addLibraries": () => (/* binding */ addLibraries),
/* harmony export */   "cleanUnusedLibraries": () => (/* binding */ cleanUnusedLibraries)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_2__);



function updateRequirements(loadingGraph, project) {
    let actualReqs = project.requirements;
    let libraries = loadingGraph.lock.reduce((acc, e) => ({ ...acc, ...{ [e.name]: e.version } }), {});
    let packs = loadingGraph.lock
        .filter(library => library.type == 'flux-pack')
        .map(library => library.name);
    let requirements = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Requirements(actualReqs.fluxComponents, Array.from(packs), libraries, loadingGraph);
    let newProject = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project(project.name, project.description, requirements, project.workflow, project.builderRendering, project.runnerRendering);
    return newProject;
}
function addLibraries(libraries, fluxPacks, project, environment) {
    let actualLibraries = project.requirements.libraries;
    let versionChecks = libraries
        .filter(lib => actualLibraries[lib.name] != undefined && actualLibraries[lib.name] != lib.version);
    if (versionChecks.length > 0)
        console.error("You can not dynamically add libraries that are already used with different version");
    let newLibraries = libraries
        .filter(lib => actualLibraries[lib.name] == undefined)
        .reduce((acc, e) => ({ ...acc, ...{ [e.name]: e.version } }), {});
    let actualPacks = project.requirements.fluxPacks;
    let newPacks = Array.from(new Set(fluxPacks.map(p => p.name)))
        .filter(pack => !actualPacks.includes(pack));
    newPacks.filter(name => {
        console.log(name, window[name]);
        return window[name] && (window[name].install || window[name].pack.install);
    })
        .forEach((name) => {
        let install = (window[name].install || window[name].pack.install)(environment);
        if (install instanceof rxjs__WEBPACK_IMPORTED_MODULE_1__.Observable)
            install.subscribe();
        if (install instanceof Promise)
            install.then(() => { });
    });
    let body = {
        libraries: {
            ...project.requirements.libraries,
            ...newLibraries
        }
    };
    return environment.getLoadingGraph(body).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.map)((loadingGraph) => {
        let newProject = updateRequirements(loadingGraph, project);
        return newProject;
    }));
}
function cleanUnusedLibraries(project, environment) {
    /*if (!environment.getLoadingGraph) {
        return of(project)
    }*/
    let setPackagesUsed = new Set([...project.workflow.modules.map(m => m.Factory.packId),
        ...project.workflow.plugins.map(m => m.Factory.packId)
    ]);
    let packagesUsed = new Array(...setPackagesUsed);
    if (packagesUsed.length == project.requirements.fluxPacks.length)
        return (0,rxjs__WEBPACK_IMPORTED_MODULE_1__.of)(project);
    let libraries = Object.entries(project.requirements.libraries)
        .filter(([k, v]) => packagesUsed.find(p => k.includes(p)))
        .reduce((acc, [k, v]) => ({ ...acc, ...{ [k]: v } }), {});
    let body = {
        libraries: libraries,
        using: project.requirements.libraries
    };
    return environment.getLoadingGraph(body).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.map)((loadingGraph) => {
        let newProject = updateRequirements(loadingGraph, project);
        return newProject;
    }));
}


/***/ }),

/***/ "./builder-editor/builder-state/app-store-description-box.ts":
/*!*******************************************************************!*\
  !*** ./builder-editor/builder-state/app-store-description-box.ts ***!
  \*******************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "addDescriptionBox": () => (/* binding */ addDescriptionBox),
/* harmony export */   "updateDescriptionBox": () => (/* binding */ updateDescriptionBox),
/* harmony export */   "deleteDescriptionBox": () => (/* binding */ deleteDescriptionBox)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);

function addDescriptionBox(descriptionBox, project) {
    let boxes = project.builderRendering.descriptionsBoxes.concat(descriptionBox);
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project(project.name, project.description, project.requirements, project.workflow, new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.BuilderRendering(project.builderRendering.modulesView, project.builderRendering.connectionsView, boxes), project.runnerRendering);
    return projectNew;
}
function updateDescriptionBox(descriptionBox, project) {
    let toKeeps = project.builderRendering.descriptionsBoxes.filter(b => b.descriptionBoxId != descriptionBox.descriptionBoxId);
    let boxes = toKeeps.concat([descriptionBox]);
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project(project.name, project.description, project.requirements, project.workflow, new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.BuilderRendering(project.builderRendering.modulesView, project.builderRendering.connectionsView, boxes), project.runnerRendering);
    return projectNew;
}
function deleteDescriptionBox(descriptionBox, project) {
    let toKeeps = project.builderRendering.descriptionsBoxes.filter(b => b.descriptionBoxId != descriptionBox.descriptionBoxId);
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project(project.name, project.description, project.requirements, project.workflow, new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.BuilderRendering(project.builderRendering.modulesView, project.builderRendering.connectionsView, toKeeps), project.runnerRendering);
    return projectNew;
}


/***/ }),

/***/ "./builder-editor/builder-state/app-store-layer.ts":
/*!*********************************************************!*\
  !*** ./builder-editor/builder-state/app-store-layer.ts ***!
  \*********************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "getLayer": () => (/* binding */ getLayer),
/* harmony export */   "cloneLayerTree": () => (/* binding */ cloneLayerTree),
/* harmony export */   "cleanChildrenLayers": () => (/* binding */ cleanChildrenLayers),
/* harmony export */   "createLayer": () => (/* binding */ createLayer)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./utils */ "./builder-editor/builder-state/utils.ts");
/* harmony import */ var _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./app-debug.environment */ "./builder-editor/builder-state/app-debug.environment.ts");



function getLayer(parentLayer, layerTree, id) {
    if (layerTree.layerId === id)
        return [layerTree, parentLayer];
    let r = undefined;
    layerTree.children.forEach(c => {
        if (!r)
            r = getLayer(layerTree, c, id);
    });
    return r;
}
function cloneLayerTree(layerTree, filter = (mdleId) => true) {
    return new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.LayerTree(layerTree.layerId, layerTree.title, layerTree.children.map(c => cloneLayerTree(c, filter)), layerTree.moduleIds.filter(mId => filter(mId)));
}
function cleanChildrenLayers(layerTree, moduleIds = undefined) {
    let children = layerTree.children.filter(c => c.moduleIds.length > 0);
    return new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.LayerTree(layerTree.layerId, layerTree.title, children.map(c => cleanChildrenLayers(c, moduleIds)), moduleIds ? layerTree.moduleIds.filter(m => moduleIds.includes(m)) : layerTree.moduleIds);
}
function createLayer(title, modules, project, currentLayerId, Factory, configuration, workflowGetter, environment) {
    let debugSingleton = _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.AppDebugEnvironment.getInstance();
    debugSingleton.debugOn &&
        debugSingleton.logWorkflowBuilder({
            level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.LogLevel.Info,
            message: "createLayer",
            object: {
                modules: modules,
                title: title
            }
        });
    let modulesId = modules.map(mdle => mdle.moduleId);
    let layer = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.LayerTree((0,_utils__WEBPACK_IMPORTED_MODULE_1__.uuidv4)(), title, [], modulesId);
    let childrenLayerInclude = modules.filter(mdle => mdle instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.GroupModules.Module).map((mdle) => mdle.layerId);
    let rootLayerTreeNew = cloneLayerTree(project.workflow.rootLayerTree);
    let parentLayer = getLayer(undefined, rootLayerTreeNew, currentLayerId)[0];
    parentLayer.moduleIds = parentLayer.moduleIds.filter(id => !modulesId.includes(id));
    parentLayer.children.filter(chidlLayer => childrenLayerInclude.includes(chidlLayer.layerId)).forEach(chidlLayer => layer.children.push(chidlLayer));
    parentLayer.children = parentLayer.children.filter(chidlLayer => !childrenLayerInclude.includes(chidlLayer.layerId));
    parentLayer.children.push(layer);
    let grpMdle = new Factory.Module({
        moduleId: Factory.id.replace("@", "_") + "_" + layer.layerId,
        configuration: configuration,
        Factory: Factory,
        workflowGetter: workflowGetter,
        layerId: layer.layerId,
        environment
    });
    let workflow = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Workflow([...project.workflow.modules, grpMdle], project.workflow.connections, project.workflow.plugins, rootLayerTreeNew);
    let moduleViewsInGrp = project.builderRendering.modulesView.filter(view => layer.moduleIds.includes(view.moduleId));
    let xWorld = moduleViewsInGrp.reduce((acc, e) => acc + e.xWorld, 0) / moduleViewsInGrp.length;
    let yWorld = moduleViewsInGrp.reduce((acc, e) => acc + e.yWorld, 0) / moduleViewsInGrp.length;
    let moduleView = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ModuleView(grpMdle.moduleId, xWorld, yWorld, Factory);
    let moduleViews = [...project.builderRendering.modulesView, moduleView];
    parentLayer.moduleIds.push(grpMdle.moduleId);
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project(project.name, project.description, project.requirements, workflow, new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.BuilderRendering(moduleViews, project.builderRendering.connectionsView, project.builderRendering.descriptionsBoxes), project.runnerRendering);
    return { project: projectNew, layer };
}


/***/ }),

/***/ "./builder-editor/builder-state/app-store-modules-group.ts":
/*!*****************************************************************!*\
  !*** ./builder-editor/builder-state/app-store-modules-group.ts ***!
  \*****************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "getDisplayedModulesView": () => (/* binding */ getDisplayedModulesView)
/* harmony export */ });
function getDisplayedModulesView(activeLayer, parentLayer, appStore, project) {
    let modulesId = activeLayer.moduleIds;
    let unitModulesView = project.builderRendering.modulesView.filter(moduleView => modulesId.includes(moduleView.moduleId));
    let parentUnitModulesView = [];
    if (parentLayer) {
        let modulesId = parentLayer.moduleIds;
        parentUnitModulesView = project.builderRendering.modulesView.filter(moduleView => modulesId.includes(moduleView.moduleId));
    }
    return {
        parentLayer: {
            modulesView: parentUnitModulesView.filter(mView => !mView.moduleId.includes(activeLayer.layerId)),
            modules: parentUnitModulesView.map(view => appStore.getModule(view.moduleId)),
            currentGroupModuleView: parentUnitModulesView.find(mView => mView.moduleId.includes(activeLayer.layerId))
        },
        currentLayer: {
            modulesView: unitModulesView,
            modules: unitModulesView.map(view => appStore.getModule(view.moduleId))
        }
    };
}


/***/ }),

/***/ "./builder-editor/builder-state/app-store-modules.ts":
/*!***********************************************************!*\
  !*** ./builder-editor/builder-state/app-store-modules.ts ***!
  \***********************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "defaultModuleRendering": () => (/* binding */ defaultModuleRendering),
/* harmony export */   "isGroupingModule": () => (/* binding */ isGroupingModule),
/* harmony export */   "addModule": () => (/* binding */ addModule),
/* harmony export */   "updateModule": () => (/* binding */ updateModule),
/* harmony export */   "alignH": () => (/* binding */ alignH),
/* harmony export */   "alignV": () => (/* binding */ alignV),
/* harmony export */   "duplicateModules": () => (/* binding */ duplicateModules),
/* harmony export */   "moveModules": () => (/* binding */ moveModules),
/* harmony export */   "deleteModules": () => (/* binding */ deleteModules)
/* harmony export */ });
/* harmony import */ var _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./app-debug.environment */ "./builder-editor/builder-state/app-debug.environment.ts");
/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./utils */ "./builder-editor/builder-state/utils.ts");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var _app_store_layer__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./app-store-layer */ "./builder-editor/builder-state/app-store-layer.ts");




function defaultModuleRendering(mdle) {
    let div = (document.createElement('div'));
    div.setAttribute("id", mdle.moduleId);
    div.setAttribute("name", mdle.configuration.title);
    div.classList.add("flux-component");
    if (mdle.moduleId.includes("viewer3d"))
        div.classList.add("fill-parent");
    if (mdle.moduleId.includes("cesium"))
        div.classList.add("fill-parent");
    return div;
}
function isGroupingModule(moduleData) {
    return ["GroupModules@flux-pack-core", "Component@flux-pack-core"].includes(moduleData.factoryId);
}
/*
export function instantiateModules( modulesData, modulesFactory, appObservables : AppObservables,
     environment, workflowGetter ): Array<ModuleFlux>{

    let debugSingleton = AppDebugEnvironment.getInstance()

    debugSingleton.debugOn &&
    debugSingleton.logWorkflowBuilder( {
        level : LogLevel.Info,
        message: "instantiateModules",
        object:{ modulesFactory: modulesFactory, modulesData:modulesData }
    })

    let modules = modulesData
    .map( moduleData => {
        let factoryKey = JSON.stringify(moduleData.factoryId)
        let Factory = modulesFactory.get(factoryKey)
        if(!Factory)
            throw Error(`Can not get factory ${factoryKey}`)
        let conf    = new Factory.Configuration({title:         moduleData.configuration.title,
                                                 description:   moduleData.configuration.description,
                                                 data:          new Factory.PersistentData(moduleData.configuration.data)
                                                })
        let data = Object.assign({},{
            moduleId:          moduleData.moduleId,
            configuration:     conf,
            ready$:            appObservables.ready$,
            Factory:           Factory,
            workflowGetter:    workflowGetter, // only relevant for Groups
            logger:            new ModuleLogger(debugSingleton),
            environment:       environment},
                isGroupingModule(moduleData) ?
                {workflowGetter, layerId:moduleData.moduleId.split(Factory.id+"_")[1] } : {})
        
        let mdle  = new Factory.Module(data)
        return mdle
    } ).filter(m => m)
    
    return modules
}
*/
function addModule(Factory, coors, project, activeLayerId, ready$, environment) {
    let debugSingleton = _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
    let configuration = new Factory.Configuration();
    let moduleId = Factory.id + "_" + (0,_utils__WEBPACK_IMPORTED_MODULE_1__.uuidv4)();
    let mdle = new Factory.Module({ moduleId, configuration, Factory, ready$, environment });
    let moduleView = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.ModuleView(mdle.moduleId, coors[0], coors[1], Factory);
    let rootLayerTreeNew = (0,_app_store_layer__WEBPACK_IMPORTED_MODULE_3__.cloneLayerTree)(project.workflow.rootLayerTree);
    let parentLayer = (0,_app_store_layer__WEBPACK_IMPORTED_MODULE_3__.getLayer)(undefined, rootLayerTreeNew, activeLayerId)[0];
    parentLayer.moduleIds.push(moduleId);
    let workflow = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Workflow(project.workflow.modules.concat(mdle), project.workflow.connections, project.workflow.plugins, rootLayerTreeNew);
    let builderRendering = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.BuilderRendering(project.builderRendering.modulesView.concat(moduleView), project.builderRendering.connectionsView, project.builderRendering.descriptionsBoxes);
    let layout = project.runnerRendering.layout;
    if (Factory.RenderView != undefined) {
        let div = defaultModuleRendering(mdle);
        layout = project.runnerRendering.layout + div.outerHTML + "\n";
    }
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Project(project.name, project.description, project.requirements, workflow, builderRendering, new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.RunnerRendering(layout, project.runnerRendering.style));
    debugSingleton.debugOn &&
        debugSingleton.logWorkflowBuilder({
            level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
            message: "add module",
            object: { factory: Factory,
                module: mdle,
                moduleView: moduleView,
                project: projectNew
            }
        });
    return projectNew;
}
function duplicate({ mdle, ready$, configuration, parent, workflow }) {
    let Factory = mdle.Factory;
    if (configuration == undefined) {
        let persistentData = new Factory.PersistentData(mdle.configuration.data);
        configuration = new Factory.Configuration({ title: mdle.configuration.title, description: mdle.configuration.description, data: persistentData });
    }
    let isPlugin = "parentModule" in mdle;
    return isPlugin ?
        new mdle.Factory.Module({
            parentModule: parent ? parent : mdle.parentModule,
            moduleId: mdle.moduleId, configuration,
            ready$,
            Factory,
            cache: mdle.cache,
            environment: mdle.environment
        }) :
        new mdle.Factory.Module(Object.assign({}, mdle, { workflow: workflow, configuration, ready$, Factory }));
}
function updateModule(mdle, configuration, project, allConnectionsSubscription, ready$) {
    let debugSingleton = _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
    let Factory = mdle.Factory;
    let isPlugin = "parentModule" in mdle;
    let newModule = duplicate({ mdle, ready$, configuration, workflow: project.workflow });
    let layerTree = project.workflow.rootLayerTree;
    if (newModule instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.GroupModules.Module) {
        layerTree = (0,_app_store_layer__WEBPACK_IMPORTED_MODULE_3__.cloneLayerTree)(project.workflow.rootLayerTree);
        (0,_app_store_layer__WEBPACK_IMPORTED_MODULE_3__.getLayer)(undefined, layerTree, newModule.layerId)[0].title = newModule.configuration.title;
    }
    let getChildrenRec = (mdle) => {
        let directChildren = project.workflow.plugins.filter(plugin => plugin.parentModule.moduleId == mdle.moduleId);
        let indirectChildren = directChildren.map(child => getChildrenRec(child)).filter(d => d.length > 0);
        if (indirectChildren.length > 0)
            throw "UPDATE MODULE: IMPLEMENTATION NOT DONE IN CASE OF NESTED PLUGINS";
        return directChildren.concat(indirectChildren.reduce((acc, e) => acc.concat(e), []));
    };
    let children = getChildrenRec(mdle);
    let toRemoveIds = [mdle.moduleId].concat(children.map(m => m.moduleId));
    let otherModules = project.workflow.modules.filter(m => !toRemoveIds.includes(m.moduleId));
    let otherPlugins = project.workflow.plugins.filter(m => !toRemoveIds.includes(m.moduleId));
    let newModules = isPlugin ? project.workflow.modules : otherModules.concat([newModule]);
    let newPlugins = isPlugin ? otherPlugins.concat([newModule]) : otherPlugins;
    newPlugins = newPlugins.concat(children.map(child => duplicate({ mdle: child, ready$, parent: newModule })));
    /*
    The module from which updates come can have some inputs/outputs that does not exist anymore.
    This piece of code select them and remove them from the current connections
    */
    let remainingInputSlots = newModule.inputSlots.map(s => s.slotId);
    let remainingOutputSlots = newModule.outputSlots.map(s => s.slotId);
    let connections = project.workflow.connections.filter((connection) => {
        if (connection.start.moduleId == newModule.moduleId && !remainingOutputSlots.includes(connection.start.slotId))
            return false;
        if (connection.end.moduleId == newModule.moduleId && !remainingInputSlots.includes(connection.end.slotId))
            return false;
        return true;
    });
    let workflow = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Workflow(newModules, connections, newPlugins, layerTree);
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Project(project.name, project.description, project.requirements, workflow, project.builderRendering, project.runnerRendering);
    debugSingleton.debugOn &&
        debugSingleton.logWorkflowBuilder({
            level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
            message: "module updated",
            object: { factory: Factory,
                newModule: newModule,
                newConfiguration: configuration,
                plugins: children,
                project: projectNew,
                newPlugins, toRemoveIds, newModules, otherModules, otherPlugins
            }
        });
    return projectNew;
}
function alignH(moduleIds, project, ready$) {
    let modulesView = project.builderRendering.modulesView.filter(m => moduleIds.includes(m.moduleId));
    let modulesViewToKeep = project.builderRendering.modulesView.filter(m => !moduleIds.includes(m.moduleId));
    let yAverage = modulesView.reduce((acc, m) => acc + m.yWorld, 0) / modulesView.length;
    let newViews = modulesView.map(m => new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.ModuleView(m.moduleId, m.xWorld, yAverage, m.Factory));
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Project(project.name, project.description, project.requirements, project.workflow, new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.BuilderRendering(modulesViewToKeep.concat(newViews), project.builderRendering.connectionsView, project.builderRendering.descriptionsBoxes), project.runnerRendering);
    return projectNew;
}
function alignV(moduleIds, project, ready$) {
    let modulesView = project.builderRendering.modulesView.filter(m => moduleIds.includes(m.moduleId));
    let modulesViewToKeep = project.builderRendering.modulesView.filter(m => !moduleIds.includes(m.moduleId));
    let xAverage = modulesView.reduce((acc, m) => acc + m.xWorld, 0) / modulesView.length;
    let newViews = modulesView.map(m => new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.ModuleView(m.moduleId, xAverage, m.yWorld, m.Factory));
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Project(project.name, project.description, project.requirements, project.workflow, new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.BuilderRendering(modulesViewToKeep.concat(newViews), project.builderRendering.connectionsView, project.builderRendering.descriptionsBoxes), project.runnerRendering);
    return projectNew;
}
function duplicateModules(modules, project, ready$) {
    let debugSingleton = _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
    let wf = project.workflow;
    let tree = project.workflow.rootLayerTree;
    let newModules = modules.map((m) => {
        let configuration = new m.Factory.Configuration({
            title: m.configuration.title,
            description: m.configuration.description,
            data: _.cloneDeep(m.configuration.data)
        });
        let moduleId = m.Factory.id + "_" + (0,_utils__WEBPACK_IMPORTED_MODULE_1__.uuidv4)();
        let mdle = new m.Factory.Module({
            moduleId, configuration, ready$, Factory: m.Factory, environment: m.environment
        });
        return mdle;
    });
    let views = project.builderRendering.modulesView.filter(mView => modules.map(m => m.moduleId).includes(mView.moduleId));
    let maxYWorld = Math.max(...views.map(mView => mView.yWorld));
    let maxXWorld = Math.max(...views.map(mView => mView.xWorld));
    let newViews = modules.map((m, i) => {
        let newView = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.ModuleView(newModules[i].moduleId, maxXWorld + (i + 1) * 50, maxYWorld + (i + 1) * 50, m.Factory);
        return newView;
    });
    let newLayerTree = (0,_app_store_layer__WEBPACK_IMPORTED_MODULE_3__.cloneLayerTree)(tree);
    modules.map((mdle, i) => {
        let layer = newLayerTree.getLayerRecursive((layer) => layer.moduleIds.includes(mdle.moduleId));
        layer.moduleIds.push(newModules[i].moduleId);
    });
    let builderRenderer = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.BuilderRendering(project.builderRendering.modulesView.concat(newViews), project.builderRendering.connectionsView, project.builderRendering.descriptionsBoxes);
    wf.rootLayerTree.moduleIds.concat(newModules.map(m => m.moduleId));
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Project(project.name, project.description, project.requirements, new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Workflow(wf.modules.concat(newModules), wf.connections, wf.plugins, newLayerTree), builderRenderer, project.runnerRendering);
    debugSingleton.debugOn &&
        debugSingleton.logWorkflowBuilder({
            level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
            message: "duplicateModules",
            object: { modules, newModules, newViews, projectNew, newLayerTree }
        });
    return projectNew;
}
function moveModules(modulesPosition, moduleViews, project, implicitModules) {
    let debugSingleton = _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
    let explicitModulesPosition = modulesPosition.map(modulePosition => [modulePosition]).reduce((acc, e) => acc.concat(e), []);
    let modulesViewToKeep = moduleViews.filter(m => !explicitModulesPosition.map(mNew => mNew.moduleId).includes(m.moduleId));
    let modulesViewNew = explicitModulesPosition
        .map(mdle => [mdle, moduleViews.find(m => m.moduleId == mdle.moduleId)])
        .filter(([mdle, mOld]) => Math.abs(mOld.xWorld - mdle.x) > 3 || Math.abs(mOld.yWorld - mdle.y) > 3)
        .map(([mdle, mOld]) => new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.ModuleView(mdle.moduleId, mdle.x, mdle.y, mOld.Factory));
    if (modulesViewNew.length == 0)
        return undefined;
    debugSingleton.debugOn &&
        debugSingleton.logWorkflowBuilder({
            level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
            message: "move modules",
            object: { modulesPosition, modulesViewToKeep, modulesViewNew }
        });
    let boxNeedUpdate = project.builderRendering.descriptionsBoxes.find(box => box.modulesId.length !== box.modulesId.filter(mId => modulesViewNew.map(m => m.moduleId).indexOf(mId) >= 0).length);
    let descriptionBoxes = boxNeedUpdate ? project.builderRendering.descriptionsBoxes.map(box => {
        if (!box.modulesId.find(mId => modulesViewNew.map(m => m.moduleId).indexOf(mId) >= 0))
            return box;
        return new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.DescriptionBox(box.descriptionBoxId, box.title, box.modulesId, box.descriptionHtml, box.properties);
    }) :
        project.builderRendering.descriptionsBoxes;
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Project(project.name, project.description, project.requirements, project.workflow, new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.BuilderRendering(modulesViewToKeep.concat(modulesViewNew), project.builderRendering.connectionsView, descriptionBoxes), project.runnerRendering);
    return projectNew;
}
function getIncludedModule(grpMdle, workflow) {
    let layer = workflow.rootLayerTree.getLayerRecursive((layer) => layer.layerId == grpMdle.layerId);
    let getModulesRec = (layer) => layer.moduleIds.concat(layer.children.reduce((acc, layer) => acc.concat(getModulesRec(layer)), []));
    return getModulesRec(layer);
}
function deleteModules(modulesDeleted, project) {
    let debugSingleton = _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
    if (modulesDeleted.length === 0)
        return undefined;
    debugSingleton.debugOn &&
        debugSingleton.logWorkflowBuilder({
            level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
            message: "deleteModules",
            object: { modulesDeleted: modulesDeleted
            }
        });
    let grpMdles = modulesDeleted.filter(mdle => mdle instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.GroupModules.Module);
    let includedModules = grpMdles.map(grpMdle => getIncludedModule(grpMdle, project.workflow));
    let modulesToDeleteId = [...modulesDeleted.map(m => m.moduleId), ...includedModules.reduce((acc, e) => acc.concat(e), [])];
    let indirectDeletedId = project.workflow.plugins
        .filter(plugin => modulesToDeleteId.includes(plugin.parentModule.moduleId))
        .map(p => p.moduleId);
    modulesToDeleteId = modulesToDeleteId.concat(indirectDeletedId);
    let newLayerTree = (0,_app_store_layer__WEBPACK_IMPORTED_MODULE_3__.cloneLayerTree)(project.workflow.rootLayerTree, (mId) => !modulesToDeleteId.includes(mId));
    newLayerTree = (0,_app_store_layer__WEBPACK_IMPORTED_MODULE_3__.cleanChildrenLayers)(newLayerTree);
    let modules = project.workflow.modules
        .filter(m => !modulesToDeleteId.includes(m.moduleId));
    let pluginsToKeep = project.workflow.plugins
        .filter(m => !modulesToDeleteId.includes(m.moduleId));
    console.log("modules", modules);
    let modulesView = project.builderRendering.modulesView
        .filter(m => !modulesToDeleteId.includes(m.moduleId));
    let connectionsToKeep = project.workflow.connections
        .filter(c => !modulesToDeleteId.includes(c.end.moduleId) &&
        !modulesToDeleteId.includes(c.start.moduleId));
    let workflow = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Workflow(modules, connectionsToKeep, pluginsToKeep, newLayerTree);
    let boxNeedUpdate = project.builderRendering.descriptionsBoxes.find(box => box.modulesId.length !== box.modulesId.filter(mId => modulesDeleted.map(m => m.moduleId).indexOf(mId) >= 0).length);
    let descriptionBoxes = boxNeedUpdate ? project.builderRendering.descriptionsBoxes.map(box => {
        let moduleIdsToKeep = box.modulesId.filter(mId => modulesDeleted.map(m => m.moduleId).indexOf(mId) < 0);
        if (moduleIdsToKeep.length == box.modulesId.length)
            return box;
        console.log("REMOVE MODULE FORM DBOX", moduleIdsToKeep);
        return new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.DescriptionBox(box.descriptionBoxId, box.title, moduleIdsToKeep, box.descriptionHtml, box.properties);
    }) :
        project.builderRendering.descriptionsBoxes;
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Project(project.name, project.description, project.requirements, workflow, new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.BuilderRendering(modulesView, project.builderRendering.connectionsView, descriptionBoxes), project.runnerRendering);
    return projectNew;
}


/***/ }),

/***/ "./builder-editor/builder-state/app-store-plugins.ts":
/*!***********************************************************!*\
  !*** ./builder-editor/builder-state/app-store-plugins.ts ***!
  \***********************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "getAvailablePlugins": () => (/* binding */ getAvailablePlugins),
/* harmony export */   "getPlugins": () => (/* binding */ getPlugins),
/* harmony export */   "addPlugin": () => (/* binding */ addPlugin)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./app-debug.environment */ "./builder-editor/builder-state/app-debug.environment.ts");
/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./utils */ "./builder-editor/builder-state/utils.ts");



function getAvailablePlugins(mdle, pluginsFactory) {
    let plugins = [];
    Array.from(pluginsFactory.entries()).forEach(([k, v]) => {
        if (mdle.factory && v.parentModule === mdle.factory.id)
            plugins.push({
                factoryId: k, pluginFactory: v
            });
    });
    return plugins;
}
function getPlugins(moduleId, project) {
    return project.workflow.plugins.filter(plugin => plugin.parentModule.moduleId === moduleId);
}
function addPlugin(Factory, parentModule, project, ready$, environment) {
    let debugSingleton = _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__.AppDebugEnvironment.getInstance();
    let configuration = new Factory.Configuration();
    let moduleId = Factory.id + "_" + (0,_utils__WEBPACK_IMPORTED_MODULE_2__.uuidv4)();
    let plugin = new Factory.Module({ parentModule, moduleId, configuration, Factory, ready$, environment });
    debugSingleton.debugOn &&
        debugSingleton.logWorkflowBuilder({
            level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__.LogLevel.Info,
            message: "add plugin",
            object: { plugin: plugin,
                pluginFactory: Factory }
        });
    let workflow = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Workflow(project.workflow.modules, project.workflow.connections, project.workflow.plugins.concat([plugin]), project.workflow.rootLayerTree);
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project(project.name, project.description, project.requirements, workflow, project.builderRendering, project.runnerRendering);
    return projectNew;
}


/***/ }),

/***/ "./builder-editor/builder-state/app-store-runner-rendering.ts":
/*!********************************************************************!*\
  !*** ./builder-editor/builder-state/app-store-runner-rendering.ts ***!
  \********************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "setRenderingLayout": () => (/* binding */ setRenderingLayout),
/* harmony export */   "setRenderingStyle": () => (/* binding */ setRenderingStyle)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./app-debug.environment */ "./builder-editor/builder-state/app-debug.environment.ts");


function setRenderingLayout(layout, project) {
    let debugSingleton = _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__.AppDebugEnvironment.getInstance();
    debugSingleton.debugOn &&
        debugSingleton.logWorkflowBuilder({
            level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__.LogLevel.Info,
            message: "set rendering layout",
            object: { layout: layout
            }
        });
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project(project.name, project.description, project.requirements, project.workflow, project.builderRendering, new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.RunnerRendering(layout, project.runnerRendering.style));
    return projectNew;
}
function setRenderingStyle(style, project) {
    let debugSingleton = _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__.AppDebugEnvironment.getInstance();
    debugSingleton.debugOn &&
        debugSingleton.logWorkflowBuilder({
            level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__.LogLevel.Info,
            message: "set rendering style",
            object: { style: style
            }
        });
    let projectNew = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project(project.name, project.description, project.requirements, project.workflow, project.builderRendering, new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.RunnerRendering(project.runnerRendering.layout, style));
    return projectNew;
}


/***/ }),

/***/ "./builder-editor/builder-state/app-store.ts":
/*!***************************************************!*\
  !*** ./builder-editor/builder-state/app-store.ts ***!
  \***************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "UiState": () => (/* binding */ UiState),
/* harmony export */   "AppStore": () => (/* binding */ AppStore)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _app_observables_service__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./app-observables.service */ "./builder-editor/builder-state/app-observables.service.ts");
/* harmony import */ var _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./app-debug.environment */ "./builder-editor/builder-state/app-debug.environment.ts");
/* harmony import */ var _observables_plotters__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./observables-plotters */ "./builder-editor/builder-state/observables-plotters.ts");
/* harmony import */ var _app_extensions_observables_service__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./app-extensions-observables.service */ "./builder-editor/builder-state/app-extensions-observables.service.ts");
/* harmony import */ var _factory_utils__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./factory-utils */ "./builder-editor/builder-state/factory-utils.ts");
/* harmony import */ var _app_store_modules__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! ./app-store-modules */ "./builder-editor/builder-state/app-store-modules.ts");
/* harmony import */ var _app_store_plugins__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! ./app-store-plugins */ "./builder-editor/builder-state/app-store-plugins.ts");
/* harmony import */ var _app_store_connections__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(/*! ./app-store-connections */ "./builder-editor/builder-state/app-store-connections.ts");
/* harmony import */ var _app_store_description_box__WEBPACK_IMPORTED_MODULE_9__ = __webpack_require__(/*! ./app-store-description-box */ "./builder-editor/builder-state/app-store-description-box.ts");
/* harmony import */ var _app_store_runner_rendering__WEBPACK_IMPORTED_MODULE_10__ = __webpack_require__(/*! ./app-store-runner-rendering */ "./builder-editor/builder-state/app-store-runner-rendering.ts");
/* harmony import */ var _app_store_layer__WEBPACK_IMPORTED_MODULE_11__ = __webpack_require__(/*! ./app-store-layer */ "./builder-editor/builder-state/app-store-layer.ts");
/* harmony import */ var _app_store_modules_group__WEBPACK_IMPORTED_MODULE_12__ = __webpack_require__(/*! ./app-store-modules-group */ "./builder-editor/builder-state/app-store-modules-group.ts");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_13__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_13___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_13__);
/* harmony import */ var _project_delta__WEBPACK_IMPORTED_MODULE_14__ = __webpack_require__(/*! ./project-delta */ "./builder-editor/builder-state/project-delta.ts");
/* harmony import */ var lodash__WEBPACK_IMPORTED_MODULE_15__ = __webpack_require__(/*! lodash */ "lodash");
/* harmony import */ var lodash__WEBPACK_IMPORTED_MODULE_15___default = /*#__PURE__*/__webpack_require__.n(lodash__WEBPACK_IMPORTED_MODULE_15__);
/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_16__ = __webpack_require__(/*! ./utils */ "./builder-editor/builder-state/utils.ts");
/* harmony import */ var _extension__WEBPACK_IMPORTED_MODULE_17__ = __webpack_require__(/*! ./extension */ "./builder-editor/builder-state/extension.ts");
/* harmony import */ var _app_store_dependencies__WEBPACK_IMPORTED_MODULE_18__ = __webpack_require__(/*! ./app-store-dependencies */ "./builder-editor/builder-state/app-store-dependencies.ts");



















class UiState {
    constructor(mode, rendererEditorsVisible, isEditing) {
        this.mode = mode;
        this.rendererEditorsVisible = rendererEditorsVisible;
        this.isEditing = isEditing;
    }
}
class AppStore {
    constructor(environment, appObservables, appBuildViewObservables) {
        this.environment = environment;
        this.appObservables = appObservables;
        this.appBuildViewObservables = appBuildViewObservables;
        this.debugSingleton = _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.AppDebugEnvironment.getInstance();
        this.builderViewsActions = {
            configurationUpdated: (data) => this.updateModule(data.module, data.configuration)
        };
        this.allSubscriptions = new Map();
        this.projectId = undefined;
        this.project = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Project("new project", "", new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Requirements([], [], {}, {}), new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Workflow([], [], [], new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.LayerTree("", "", [], [])), new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.BuilderRendering([], [], []), new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.RunnerRendering("", ""));
        this.activeLayerId = this.project.workflow.rootLayerTree.layerId;
        this.adaptors = [];
        this.history = new Array(this.project);
        this.indexHistory = 0;
        this.uiState = new UiState("combined", false, false);
        this.packages = [];
        this.implicitModules = [];
        this.moduleSelected = undefined;
        this.modulesSelected = [];
        this.connectionSelected = undefined;
        this.descriptionBoxSelected = undefined;
        this.appExtensionsObservables = _app_extensions_observables_service__WEBPACK_IMPORTED_MODULE_4__.AppExtensionsObservables.getInstance();
        this.environment = environment;
        this.debugSingleton.logWorkflowBuilder({
            level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.LogLevel.Info,
            message: "AppStore constructed",
            object: { appStore: this }
        });
        _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.GroupModules.BuilderView.notifier$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_13__.filter)((event) => event.type == "layerFocused")).subscribe(d => this.selectActiveLayer(d.data));
        _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Component.BuilderView.notifier$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_13__.filter)((event) => event.type == "layerFocused")).subscribe(d => this.selectActiveLayer(d.data));
        _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.GroupModules.BuilderView.notifier$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_13__.filter)((event) => event.type == "closeLayer")).subscribe(d => this.selectActiveLayer(this.getParentLayer(d.data).layerId));
        _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Component.BuilderView.notifier$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_13__.filter)((event) => event.type == "closeLayer")).subscribe(d => this.selectActiveLayer(this.getParentLayer(d.data).layerId));
        this.appObservables.renderingLoaded$.next({ style: "", layout: "", cssLinks: [] });
    }
    static getInstance(environment) {
        if (!AppStore.instance)
            AppStore.instance = new AppStore(environment, _app_observables_service__WEBPACK_IMPORTED_MODULE_1__.AppObservables.getInstance(), _observables_plotters__WEBPACK_IMPORTED_MODULE_3__.AppBuildViewObservables.getInstance());
        return AppStore.instance;
    }
    setUiState(state) {
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowBuilder({
                level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.LogLevel.Info,
                message: "ui state updated",
                object: { state: state }
            });
        this.uiState = state;
        this.appObservables.uiStateUpdated$.next(this.uiState);
    }
    loadProject(projectId, project, onEvent) {
        this.projectId = projectId;
        let project$ = (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.loadProjectDependencies$)(project, this.environment, onEvent).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_13__.map)(({ project, packages }) => {
            return (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.createProject)(project, packages, () => this.project.workflow, this.allSubscriptions, this.environment);
        }));
        this.initializeProject(project$);
    }
    loadProjectId(projectId) {
        this.projectId = projectId;
        let project$ = (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.loadProjectDatabase$)(projectId, () => this.project.workflow, this.allSubscriptions, this.environment);
        this.initializeProject(project$);
    }
    loadProjectURI(projectURI) {
        this.projectId = undefined;
        let project$ = (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.loadProjectURI$)(projectURI, () => this.project.workflow, this.allSubscriptions, this.environment);
        this.initializeProject(project$);
    }
    initializeProject(project$) {
        project$.subscribe(({ project, packages }) => {
            this.appObservables.packagesUpdated$.next(packages);
            this.activeLayerId = project.workflow.rootLayerTree.layerId;
            this.debugSingleton.debugOn &&
                this.debugSingleton.logWorkflowBuilder({
                    level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.LogLevel.Info,
                    message: "project created",
                    object: { project: this.project }
                });
            this.updateProject(project);
            this.loadExtensions();
            this.appObservables.ready$.next(true);
            this.appObservables.packagesLoaded$.next();
            this.appObservables.uiStateUpdated$.next(this.uiState);
            this.appObservables.renderingLoaded$.next({
                style: project.runnerRendering.style,
                layout: project.runnerRendering.layout, cssLinks: []
            });
        });
    }
    loadExtensions() {
        // this test is for backward compatibility w/ flux-lib-core
        if (!_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.FluxExtensionAPIs)
            return;
        _extension__WEBPACK_IMPORTED_MODULE_17__.BuilderStateAPI.initialize(this);
        _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.FluxExtensionAPIs.registerAPI('BuilderState', _extension__WEBPACK_IMPORTED_MODULE_17__.BuilderStateAPI);
    }
    addLibraries$(libraries, fluxPacks) {
        return (0,_app_store_dependencies__WEBPACK_IMPORTED_MODULE_18__.addLibraries)(libraries, fluxPacks, this.project, this.environment).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_13__.tap)((newProject) => {
            this.updateProject(newProject);
        }));
    }
    projectSchema$() {
        return (0,_app_store_dependencies__WEBPACK_IMPORTED_MODULE_18__.cleanUnusedLibraries)(this.project, this.environment).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_13__.map)(project => (0,_factory_utils__WEBPACK_IMPORTED_MODULE_5__.toProjectData)(project)));
    }
    projectURI$() {
        return this.projectSchema$().pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_13__.map)(project => {
            return `/ui/flux-builder/?uri=${(0,_factory_utils__WEBPACK_IMPORTED_MODULE_5__.toProjectURI)(project)}`;
        }));
    }
    saveProject() {
        this.projectSchema$().pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_13__.mergeMap)(body => this.environment.postProject(this.projectId, body).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_13__.map)(() => body))))
            .subscribe((body) => {
            this.debugSingleton.debugOn &&
                this.debugSingleton.logWorkflowBuilder({
                    level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.LogLevel.Info,
                    message: "project saved",
                    object: { body, project: this.project }
                });
        });
    }
    getModulesFactory() {
        return this.packages
            .map(p => Object.entries(p.modules).map(([_, mdle]) => [`${mdle.id}@${p.id}`, mdle]))
            .reduce((acc, e) => acc.concat(e), [])
            .reduce((acc, e) => lodash__WEBPACK_IMPORTED_MODULE_15__.merge(acc, { [e[0]]: e[1] }), {});
    }
    getAvailablePlugins(mdle) {
        return (0,_app_store_plugins__WEBPACK_IMPORTED_MODULE_7__.getAvailablePlugins)(mdle, this.pluginsFactory);
    }
    getPlugins(moduleId) {
        return (0,_app_store_plugins__WEBPACK_IMPORTED_MODULE_7__.getPlugins)(moduleId, this.project);
    }
    addPlugin(Factory, parentModule) {
        let project = (0,_app_store_plugins__WEBPACK_IMPORTED_MODULE_7__.addPlugin)(Factory, parentModule, this.project, this.appObservables.ready$, this.environment);
        this.updateProject(project);
        return project.workflow.plugins.slice(-1)[0];
    }
    addModule(moduleFactory, coors = [0, 0]) {
        let project = (0,_app_store_modules__WEBPACK_IMPORTED_MODULE_6__.addModule)(moduleFactory, coors, this.project, this.activeLayerId, this.appObservables.ready$, this.environment);
        this.updateProject(project);
        return project.workflow.modules.slice(-1)[0];
    }
    updateModule(mdle, configuration) {
        let project = (0,_app_store_modules__WEBPACK_IMPORTED_MODULE_6__.updateModule)(mdle, configuration, this.project, this.allSubscriptions, this.appObservables.ready$);
        this.unselect();
        this.updateProject(project);
    }
    duplicateModules(modules) {
        let project = (0,_app_store_modules__WEBPACK_IMPORTED_MODULE_6__.duplicateModules)(modules, this.project, this.appObservables.ready$);
        this.updateProject(project);
    }
    alignH(modules) {
        let project = (0,_app_store_modules__WEBPACK_IMPORTED_MODULE_6__.alignH)(modules.map(m => m.moduleId), this.project, this.appObservables.ready$);
        this.updateProject(project);
    }
    alignV(modules) {
        let project = (0,_app_store_modules__WEBPACK_IMPORTED_MODULE_6__.alignV)(modules.map(m => m.moduleId), this.project, this.appObservables.ready$);
        this.updateProject(project);
    }
    moveModules(modulesPosition) {
        modulesPosition = modulesPosition.filter(m => this.getActiveLayer().moduleIds.includes(m.moduleId));
        let project = (0,_app_store_modules__WEBPACK_IMPORTED_MODULE_6__.moveModules)(modulesPosition, this.project.builderRendering.modulesView, this.project, this.implicitModules);
        this.updateProject(project);
    }
    getModuleSelected() {
        if (this.moduleSelected)
            return this.moduleSelected;
        if (this.modulesSelected.length == 1)
            return this.modulesSelected[0];
        return undefined;
    }
    getModulesSelected() {
        if (this.moduleSelected)
            return [this.moduleSelected];
        if (this.modulesSelected.length > 0)
            return this.modulesSelected;
        return [];
    }
    isSelected(moduleId) {
        if (this.moduleSelected && this.moduleSelected.moduleId === moduleId)
            return true;
        if (this.modulesSelected && this.modulesSelected.find(m => m.moduleId === moduleId))
            return true;
        return false;
    }
    selectModule(moduleId) {
        if (this.modulesSelected.find(m => m.moduleId == moduleId) ||
            (this.moduleSelected && this.moduleSelected.moduleId == moduleId))
            return;
        if (this.moduleSelected && this.moduleSelected.moduleId != moduleId) {
            this.appObservables.modulesUnselected$.next([this.moduleSelected]);
            this.moduleSelected = undefined;
        }
        if (!this.modulesSelected.find(m => m.moduleId == moduleId)) {
            this.appObservables.modulesUnselected$.next(this.modulesSelected);
            this.modulesSelected = [];
        }
        this.moduleSelected = this.getModule(moduleId);
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowBuilder({
                level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.LogLevel.Info,
                message: "module selected",
                object: { module: this.moduleSelected
                }
            });
        this.appObservables.moduleSelected$.next(this.moduleSelected);
    }
    selectConnection(connection) {
        this.unselect();
        this.connectionSelected = connection;
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowBuilder({
                level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.LogLevel.Info,
                message: "connection selected",
                object: { module: this.connectionSelected
                }
            });
        this.appObservables.connectionSelected$.next(this.connectionSelected);
        let moduleFrom = this.getModule(this.connectionSelected.start.moduleId);
        let moduleTo = this.getModule(this.connectionSelected.end.moduleId);
        let suggestions = this.adaptors.filter(a => a.fromModuleFactoryId === moduleFrom["factoryId"] &&
            a.toModuleFactoryId === moduleTo["factoryId"] &&
            a.fromModuleSlotId === this.connectionSelected.start.slotId &&
            a.toModuleSlotId === this.connectionSelected.end.slotId);
        if (!this.connectionSelected.adaptor)
            this.appObservables.suggestions$.next(suggestions);
    }
    select({ modulesId, connectionsId }) {
        this.unselect();
        this.modulesSelected = this.project.workflow.modules.filter(m => modulesId.includes(m.moduleId));
        this.modulesSelected.forEach(m => this.appObservables.moduleSelected$.next(m));
    }
    getModuleOrPlugin(moduleId) {
        let allModules = this.getModulesAndPlugins();
        let m = allModules.find(m => m.moduleId === moduleId);
        return m;
    }
    getModule(moduleId) {
        let m = this.getModulesAndPlugins().find(m => m.moduleId === moduleId);
        if (m)
            return m;
        m = this.implicitModules.find(m => m.moduleId === moduleId);
        return m;
    }
    deleteModules(modulesDeleted) {
        this.unselect();
        let project = (0,_app_store_modules__WEBPACK_IMPORTED_MODULE_6__.deleteModules)(modulesDeleted, this.project);
        if (!project)
            return;
        if (!(0,_app_store_layer__WEBPACK_IMPORTED_MODULE_11__.getLayer)(project.workflow.rootLayerTree, project.workflow.rootLayerTree, this.activeLayerId)) {
            let oldLayer = this.activeLayerId;
            this.activeLayerId = project.workflow.rootLayerTree.layerId;
            this.updateProject(project);
            this.appObservables.activeLayerUpdated$.next({ fromLayerId: oldLayer, toLayerId: this.activeLayerId });
            return;
        }
        this.updateProject(project);
    }
    deleteModule(mdle) {
        if (mdle == this.moduleSelected)
            this.unselect();
        this.deleteModules([mdle]);
    }
    getActiveLayer() {
        return this.getLayer(this.activeLayerId);
    }
    getLayer(layerId) {
        let a = (0,_app_store_layer__WEBPACK_IMPORTED_MODULE_11__.getLayer)(undefined, this.project.workflow.rootLayerTree, layerId);
        if (a == undefined) {
            console.error("Can not find layer ", layerId);
            return undefined;
        }
        return a[0];
    }
    getParentLayer(layerId) {
        return (0,_app_store_layer__WEBPACK_IMPORTED_MODULE_11__.getLayer)(undefined, this.project.workflow.rootLayerTree, layerId)[1];
    }
    selectActiveLayer(layerId) {
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowBuilder({
                level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.LogLevel.Info,
                message: "selectActiveLayer",
                object: {
                    layerId: layerId,
                    layers: this.project.workflow.rootLayerTree
                }
            });
        if (this.activeLayerId == layerId)
            return;
        let oldLayerId = this.activeLayerId;
        this.activeLayerId = layerId;
        this.appBuildViewObservables.modulesViewUpdated$.next(this.getActiveModulesView());
        this.appObservables.descriptionsBoxesUpdated$.next(this.project.builderRendering.descriptionsBoxes);
        this.appObservables.activeLayerUpdated$.next({ fromLayerId: oldLayerId, toLayerId: layerId });
        //this.addDescriptionBox(descriptionBox)
    }
    getActiveModulesId() {
        return this.getLayer(this.activeLayerId).moduleIds;
    }
    getActiveModulesView() {
        //deprecated, use getDisplayedModulesView, need to remove from tests
        const displayed = this.getDisplayedModulesView();
        return [...displayed.currentLayer.modulesView, ...displayed.parentLayer.modulesView];
    }
    getDisplayedModulesView() {
        let activeLayer = this.getLayer(this.activeLayerId);
        let parentLayer = this.getParentLayer(this.activeLayerId);
        return (0,_app_store_modules_group__WEBPACK_IMPORTED_MODULE_12__.getDisplayedModulesView)(activeLayer, parentLayer, this, this.project);
    }
    getGroupModule(layerId) {
        return this.project.workflow.modules.find(m => m instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.GroupModules.Module && m.layerId == layerId);
    }
    getParentGroupModule(moduleId) {
        let mdle = this.getModule(moduleId);
        if (this.project.workflow.plugins.map(plugin => plugin.moduleId).includes(mdle.moduleId))
            mdle = mdle.parentModule;
        let layer = this.project.workflow.rootLayerTree.getLayerRecursive(layer => layer.moduleIds.includes(mdle.moduleId));
        if (!layer)
            return undefined;
        return this.project.workflow.modules.find(mdle => mdle.moduleId.includes(layer.layerId));
    }
    getChildrenRecursive(layerId) {
        let layer = this.getLayer(layerId);
        let all = layer.getChildrenModules();
        return all;
    }
    getModulesAndPlugins() {
        return this.project.workflow.modules.concat(this.project.workflow.plugins);
    }
    addRemoteComponent(componentId, [x, y]) {
        /*Backend.getComponent(componentId).subscribe( component=> {
            let project = addRemoteComponent(component, this.modulesFactory,[x,y],this.project, this.activeLayerId,
                (_)=>this.project.workflow, this.appObservables.ready$, this.environment)
            console.log("New project!", project)
            this.updateProject(project)
            }
        )
        */
    }
    getConnection(connectionId) {
        let c = this.project.workflow.connections.find(c => c.connectionId === connectionId);
        return c;
    }
    addConnection(connection) {
        let project = (0,_app_store_connections__WEBPACK_IMPORTED_MODULE_8__.addConnection)(connection, this.project, this.allSubscriptions);
        this.updateProject(project);
        this.unselect();
        this.appObservables.connectionsUpdated$.next(this.project.workflow.connections);
    }
    setConnectionView(connection, properties) {
        let project = (0,_app_store_connections__WEBPACK_IMPORTED_MODULE_8__.setConnectionView)(connection, properties, this.project);
        this.updateProject(project);
        this.unselect();
        this.appObservables.connectionsUpdated$.next(this.project.workflow.connections);
    }
    getConnectionSelected() {
        return this.connectionSelected;
    }
    getConnectionView(connectionId) {
        return this.project.builderRendering.connectionsView.find(c => c.connectionId == connectionId);
    }
    deleteConnection(connection) {
        if (this.connectionSelected === connection) {
            this.connectionSelected = undefined;
            this.appObservables.unselect$.next();
        }
        let project = (0,_app_store_connections__WEBPACK_IMPORTED_MODULE_8__.deleteConnection)(connection, this.project, this.allSubscriptions);
        this.updateProject(project);
        this.appObservables.connectionsUpdated$.next(this.project.workflow.connections);
    }
    addAdaptor(adaptor, connection) {
        let project = (0,_app_store_connections__WEBPACK_IMPORTED_MODULE_8__.addAdaptor)(connection, adaptor, this.project, this.allSubscriptions);
        this.updateProject(project);
        this.appObservables.connectionsUpdated$.next(this.project.workflow.connections);
    }
    deleteAdaptor(connection) {
        let project = (0,_app_store_connections__WEBPACK_IMPORTED_MODULE_8__.deleteAdaptor)(connection, this.project, this.allSubscriptions);
        this.updateProject(project);
        this.appObservables.connectionsUpdated$.next(this.project.workflow.connections);
    }
    publishAdaptor(connection) {
        /*this.environment.backend.postAdaptor({
            adaptorId:connection.adaptor.adaptorId,
            fromModuleFactoryId: this.getModule(connection.start.moduleId)["factoryId"],
            toModuleFactoryId: this.getModule(connection.end.moduleId)["factoryId"],
            fromModuleSlotId:connection.start.slotId,
            toModuleSlotId:connection.end.slotId,
            configuration:connection.adaptor.configuration
            }).subscribe(()=> console.log("adaptor published"))
            */
    }
    updateAdaptor(connection, mappingFunction) {
        let project = (0,_app_store_connections__WEBPACK_IMPORTED_MODULE_8__.updateAdaptor)(connection, mappingFunction, this.project, this.allSubscriptions);
        this.updateProject(project);
        this.appObservables.connectionsUpdated$.next(this.project.workflow.connections);
    }
    unselect() {
        this.modulesSelected = [];
        this.moduleSelected = undefined;
        this.connectionSelected = undefined;
        this.descriptionBoxSelected = undefined;
        this.appObservables.unselect$.next();
        this.appObservables.suggestions$.next([]);
    }
    deleteSelected() {
        if (this.uiState.isEditing)
            return;
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowBuilder({
                level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.LogLevel.Info,
                message: "delete selected",
                object: { connectionSelected: this.connectionSelected,
                    moduleSelected: this.moduleSelected,
                    modulesSelected: this.modulesSelected,
                    descriptionBoxSelected: this.descriptionBoxSelected
                }
            });
        if (this.connectionSelected) {
            this.deleteConnection(this.connectionSelected);
        }
        if (this.moduleSelected) {
            this.deleteModule(this.moduleSelected);
        }
        if (this.modulesSelected && this.modulesSelected.length > 0) {
            this.deleteModules(this.modulesSelected);
        }
        if (this.descriptionBoxSelected) {
            this.deleteDescriptionBox(this.descriptionBoxSelected);
        }
        this.appObservables.suggestions$.next([]);
    }
    addDescriptionBox(descriptionBox) {
        let project = (0,_app_store_description_box__WEBPACK_IMPORTED_MODULE_9__.addDescriptionBox)(descriptionBox, this.project);
        this.updateProject(project);
        this.appObservables.descriptionsBoxesUpdated$.next(this.project.builderRendering.descriptionsBoxes);
    }
    selectDescriptionBox(descriptionBoxId) {
        this.unselect();
        this.descriptionBoxSelected = this.project.builderRendering.descriptionsBoxes.find(b => b.descriptionBoxId == descriptionBoxId);
        this.appObservables.descriptionsBoxesUpdated$.next(this.project.builderRendering.descriptionsBoxes);
    }
    deleteDescriptionBox(descriptionBox) {
        if (descriptionBox == this.descriptionBoxSelected)
            this.unselect();
        let project = (0,_app_store_description_box__WEBPACK_IMPORTED_MODULE_9__.deleteDescriptionBox)(descriptionBox, this.project);
        this.updateProject(project);
        this.appObservables.descriptionsBoxesUpdated$.next(this.project.builderRendering.descriptionsBoxes);
    }
    addGroup(moduleIds) {
        let dBox = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.DescriptionBox((0,_utils__WEBPACK_IMPORTED_MODULE_16__.uuidv4)(), "grouped module", moduleIds, "", new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.DescriptionBoxProperties(undefined));
        let config = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.GroupModules.Configuration({ title: dBox.title });
        let { project } = (0,_app_store_layer__WEBPACK_IMPORTED_MODULE_11__.createLayer)(dBox.title, dBox.modulesId.map(mid => this.getModule(mid)), this.project, this.activeLayerId, _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.GroupModules, config, (_) => this.project.workflow, this.environment);
        this.updateProject(project);
    }
    addComponent(moduleIds) {
        let dBox = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.DescriptionBox((0,_utils__WEBPACK_IMPORTED_MODULE_16__.uuidv4)(), "component", moduleIds, "", new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.DescriptionBoxProperties(undefined));
        let config = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Component.Configuration({ title: dBox.title });
        let { project } = (0,_app_store_layer__WEBPACK_IMPORTED_MODULE_11__.createLayer)(dBox.title, dBox.modulesId.map(mid => this.getModule(mid)), this.project, this.activeLayerId, _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Component, config, (_) => this.project.workflow, this.environment);
        this.updateProject(project);
    }
    publishComponent(component) {
        let data = (0,_utils__WEBPACK_IMPORTED_MODULE_16__.packageAssetComponent)(component, this.project);
        sessionStorage.setItem(component.moduleId, JSON.stringify(data));
        window.open("/ui/assets-publish-ui?kind=flux-component&related_id=" + component.moduleId, '_blank');
    }
    projectSettings() {
        window.open("/ui/assets-publish-ui?kind=flux-project&related_id=" + this.projectId, '_blank');
    }
    updateDescriptionBox(descriptionBox) {
        this.unselect();
        let project = (0,_app_store_description_box__WEBPACK_IMPORTED_MODULE_9__.updateDescriptionBox)(descriptionBox, this.project);
        this.updateProject(project);
        this.appObservables.descriptionsBoxesUpdated$.next(this.project.builderRendering.descriptionsBoxes);
    }
    setRenderingLayout(layout, asNewState = true) {
        let project = (0,_app_store_runner_rendering__WEBPACK_IMPORTED_MODULE_10__.setRenderingLayout)(layout, this.project);
        this.updateProject(project, asNewState);
    }
    applyStyle() {
        this.appObservables.cssUpdated$.next(this.project.runnerRendering.style);
    }
    setRenderingStyle(style, asNewState = true) {
        let project = (0,_app_store_runner_rendering__WEBPACK_IMPORTED_MODULE_10__.setRenderingStyle)(style, this.project);
        this.updateProject(project, asNewState);
    }
    addModuleRenderDiv(outerHtml) {
        let newLayout = this.project.runnerRendering.layout + outerHtml + "\n";
        this.setRenderingLayout(newLayout);
    }
    updateProjectToIndexHistory(indexHistory, oldIndex) {
        let updatesDone = {
            modules: false,
            modulesView: false,
            connections: false,
            activeLayer: false,
            descriptionBox: false
        };
        this.indexHistory = indexHistory;
        this.project = this.history[this.indexHistory];
        let oldProject = this.history[oldIndex];
        let delta = (0,_project_delta__WEBPACK_IMPORTED_MODULE_14__.workflowDelta)(oldProject.workflow, this.project.workflow);
        if (delta.modules.removedElements) {
            delta.modules.removedElements.filter(m => (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.instanceOfSideEffects)(m)).forEach(m => m.dispose());
        }
        if (delta.modules.createdElements) {
            (0,_utils__WEBPACK_IMPORTED_MODULE_16__.plugBuilderViewsSignals)(delta.modules.createdElements, this.builderViewsActions, this.appBuildViewObservables.notification$);
            delta.modules.createdElements.filter(m => (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.instanceOfSideEffects)(m)).forEach(m => m.apply());
        }
        if (!updatesDone.modules && (delta.modules.createdElements.length > 0 || delta.modules.removedElements.length > 0)) {
            this.appObservables.modulesUpdated$.next(delta.modules);
            this.appBuildViewObservables.modulesViewUpdated$.next(this.getActiveModulesView());
            updatesDone.modules = true;
            updatesDone.modulesView = true;
        }
        if (!updatesDone.connections && (delta.connections.createdElements.length > 0 || delta.connections.removedElements.length > 0)) {
            this.appObservables.connectionsUpdated$.next(this.project.workflow.connections);
            updatesDone.connections = true;
        }
        if (!updatesDone.modulesView && (this.project.builderRendering.modulesView !== oldProject.builderRendering.modulesView)) {
            let delta = (0,_project_delta__WEBPACK_IMPORTED_MODULE_14__.getDelta)(oldProject.builderRendering.modulesView, this.project.builderRendering.modulesView);
            let updates = [
                ...delta.createdElements.filter(e => delta.removedElements.find(e2 => e2.moduleId == e.moduleId) == undefined),
                ...delta.createdElements.filter(e => delta.removedElements.find(e2 => e2.moduleId == e.moduleId) == undefined)
            ];
            updates.length > 0
                ? this.appBuildViewObservables.modulesViewUpdated$.next(this.getActiveModulesView())
                : this.appObservables.connectionsUpdated$.next(this.project.workflow.connections);
            if (updates.length > 0)
                updatesDone.modulesView = true;
        }
        if (!updatesDone.activeLayer &&
            (this.activeLayerId != this.project.workflow.rootLayerTree.layerId ||
                this.project.workflow.rootLayerTree != oldProject.workflow.rootLayerTree)) {
            if (!updatesDone.modulesView)
                this.appBuildViewObservables.modulesViewUpdated$.next(this.getActiveModulesView());
            this.appObservables.descriptionsBoxesUpdated$.next(this.project.builderRendering.descriptionsBoxes);
            this.appObservables.activeLayerUpdated$.next({ fromLayerId: undefined, toLayerId: this.activeLayerId });
            updatesDone.activeLayer = true;
        }
        if (!updatesDone.descriptionBox && (this.project.builderRendering.descriptionsBoxes !== oldProject.builderRendering.descriptionsBoxes)) {
            this.appObservables.descriptionsBoxesUpdated$.next(this.project.builderRendering.descriptionsBoxes);
            updatesDone.descriptionBox = true;
        }
        (0,_app_store_connections__WEBPACK_IMPORTED_MODULE_8__.subscribeConnections)(this.allSubscriptions, delta.connections, this.project.workflow.modules, this.project.workflow.plugins);
        this.appExtensionsObservables.projectUpdated$.next(delta);
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowBuilder({
                level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.LogLevel.Info,
                message: "updateProjectToIndexHistory",
                object: { oldProject, delta, newProject: this.project, history: this.history, updatesDone }
            });
    }
    undo() {
        if (this.indexHistory == 0)
            return;
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowBuilder({
                level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.LogLevel.Info,
                message: "undo",
                object: { history: this.history }
            });
        this.updateProjectToIndexHistory(this.indexHistory - 1, this.indexHistory);
    }
    redo() {
        if (this.indexHistory == this.history.length - 1)
            return;
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowBuilder({
                level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.LogLevel.Info,
                message: "redo",
                object: { history: this.history }
            });
        this.updateProjectToIndexHistory(this.indexHistory + 1, this.indexHistory);
    }
    updateProject(newProject, asNewState = true) {
        if (!newProject)
            return;
        let oldIndex = this.indexHistory;
        if (!asNewState) {
            this.history = this.history.slice(0, -1);
            this.indexHistory--;
        }
        if (this.indexHistory === this.history.length - 1) {
            this.history.push(newProject);
            this.indexHistory++;
        }
        if (this.indexHistory < this.history.length - 1) {
            this.history = this.history.slice(0, this.indexHistory + 1);
            this.history.push(newProject);
            this.indexHistory = this.history.length - 1;
        }
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowBuilder({
                level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_2__.LogLevel.Info,
                message: "updateProject",
                object: {
                    newProject: newProject,
                    history: this.history
                }
            });
        this.updateProjectToIndexHistory(this.indexHistory, oldIndex);
    }
}
AppStore.instance = undefined;


/***/ }),

/***/ "./builder-editor/builder-state/code-editor-broadcast.ts":
/*!***************************************************************!*\
  !*** ./builder-editor/builder-state/code-editor-broadcast.ts ***!
  \***************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "CodeEditor": () => (/* binding */ CodeEditor)
/* harmony export */ });
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_1__);


var CodeEditor;
(function (CodeEditor) {
    let senderFluxChannel = new BroadcastChannel("out=>code-editor@BroadcastDrive");
    let recieverFluxChannel = new BroadcastChannel("code-editor@BroadcastDrive=>out");
    function mountBroadcastDrive(codeEditor, urlCodeEditor) {
        let ownerId = codeEditor.ownerId;
        let pingMessage = {
            action: "ping",
            channelResp: "code-editor=>flux",
            ownerId: ownerId
        };
        let isConnected = false;
        let communicationEstablished$ = new rxjs__WEBPACK_IMPORTED_MODULE_1__.BehaviorSubject(false);
        let interval$ = (0,rxjs__WEBPACK_IMPORTED_MODULE_1__.interval)(500).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_0__.take)(1));
        let mountedDrive = undefined;
        interval$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_0__.take)(1))
            .subscribe(() => {
            if (!isConnected) {
                window.open(urlCodeEditor, '_tab_code_editor');
                (0,rxjs__WEBPACK_IMPORTED_MODULE_1__.interval)(200).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_0__.filter)(() => !isConnected)).subscribe(() => senderFluxChannel.postMessage(pingMessage));
            }
        });
        senderFluxChannel.postMessage(pingMessage);
        communicationEstablished$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_0__.filter)(d => d == true), (0,rxjs_operators__WEBPACK_IMPORTED_MODULE_0__.mergeMap)(() => codeEditor.mount$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_0__.map)(d => codeEditor.drive(d)), (0,rxjs_operators__WEBPACK_IMPORTED_MODULE_0__.tap)(d => mountedDrive = d)))).subscribe((drive) => {
            let action = {
                action: "mount",
                ownerId: ownerId,
                codeEditor: { drive: { name: drive.name, data: drive.data }, UI: codeEditor.UI }
            };
            senderFluxChannel.postMessage(action);
        });
        let subs = codeEditor.unmount$.subscribe(() => {
            senderFluxChannel.postMessage({ action: "unmount", ownerId: ownerId });
            subs.unsubscribe();
        });
        recieverFluxChannel.onmessage = ({ data }) => {
            if (data.action == "ping-ack" && data.ownerId == ownerId) {
                isConnected = true;
                communicationEstablished$.next(true);
            }
            if (data.action == "updateFile" && data.ownerId == ownerId) {
                let ack = () => senderFluxChannel.postMessage({ action: "updateFile-ack", actionId: data.actionId, ownerId: ownerId });
                mountedDrive.onFileUpdated(data.data, ack);
            }
        };
    }
    CodeEditor.mountBroadcastDrive = mountBroadcastDrive;
})(CodeEditor || (CodeEditor = {}));


/***/ }),

/***/ "./builder-editor/builder-state/extension.ts":
/*!***************************************************!*\
  !*** ./builder-editor/builder-state/extension.ts ***!
  \***************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "BuilderStateAPI": () => (/* binding */ BuilderStateAPI)
/* harmony export */ });
class BuilderStateAPI {
    static initialize(appStore) {
        BuilderStateAPI.appStore = appStore;
    }
}


/***/ }),

/***/ "./builder-editor/builder-state/factory-utils.ts":
/*!*******************************************************!*\
  !*** ./builder-editor/builder-state/factory-utils.ts ***!
  \*******************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "toLayerTreeData": () => (/* binding */ toLayerTreeData),
/* harmony export */   "serializeWorkflow": () => (/* binding */ serializeWorkflow),
/* harmony export */   "toProjectData": () => (/* binding */ toProjectData),
/* harmony export */   "toProjectURI": () => (/* binding */ toProjectURI),
/* harmony export */   "fromProjectURI": () => (/* binding */ fromProjectURI)
/* harmony export */ });
function toLayerTreeData(layer) {
    return {
        layerId: layer.layerId,
        moduleIds: layer.moduleIds,
        title: layer.title,
        children: layer.children.map(d => toLayerTreeData(d))
    };
}
function serializeWorkflow(workflow) {
    return {
        modules: workflow.modules.map(mdle => ({
            moduleId: mdle.moduleId,
            factoryId: { module: mdle.Factory.id, pack: mdle.Factory.packId },
            configuration: { title: mdle.configuration.title,
                description: mdle.configuration.description,
                data: Object.assign({}, mdle.configuration.data) }
        })),
        connections: workflow.connections.map(c => Object.assign({
            end: {
                moduleId: c.end.moduleId,
                slotId: c.end.slotId,
            },
            start: {
                moduleId: c.start.moduleId,
                slotId: c.start.slotId,
            }
        }, c.adaptor ?
            { adaptor: {
                    adaptorId: c.adaptor.adaptorId,
                    mappingFunction: c.adaptor.toString()
                }
            } : {})),
        plugins: workflow.plugins.map(plugin => ({
            parentModuleId: plugin.parentModule.moduleId,
            moduleId: plugin.moduleId,
            factoryId: { module: plugin.Factory.id, pack: plugin.Factory.packId },
            configuration: { title: plugin.configuration.title,
                description: plugin.configuration.description,
                data: Object.assign({}, plugin.configuration.data) }
        })),
        rootLayerTree: toLayerTreeData(workflow.rootLayerTree)
    };
}
function toProjectData(project) {
    return {
        name: project.name,
        description: project.description,
        runnerRendering: project.runnerRendering,
        builderRendering: {
            descriptionsBoxes: project.builderRendering.descriptionsBoxes.map(d => ({ descriptionBoxId: d.descriptionBoxId,
                descriptionHtml: d.descriptionHtml,
                modulesId: d.modulesId,
                title: d.title,
                properties: {
                    color: d.properties.color
                }
            })),
            modulesView: project.builderRendering.modulesView.map(m => ({
                moduleId: m.moduleId,
                xWorld: m.xWorld,
                yWorld: m.yWorld
            })),
            connectionsView: project.builderRendering.connectionsView.map(c => ({
                connectionId: c.connectionId,
                wireless: c.wireless
            }))
        },
        requirements: project.requirements,
        workflow: serializeWorkflow(project.workflow)
    };
}
function toProjectURI(projectData) {
    return encodeURIComponent(JSON.stringify(projectData));
}
function fromProjectURI(uri) {
    return JSON.parse(decodeURIComponent(uri));
}


/***/ }),

/***/ "./builder-editor/builder-state/index.ts":
/*!***********************************************!*\
  !*** ./builder-editor/builder-state/index.ts ***!
  \***********************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "AppDebugEnvironment": () => (/* reexport safe */ _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment),
/* harmony export */   "LogEntry": () => (/* reexport safe */ _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.LogEntry),
/* harmony export */   "LogLevel": () => (/* reexport safe */ _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.LogLevel),
/* harmony export */   "LogerConsole": () => (/* reexport safe */ _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__.LogerConsole),
/* harmony export */   "fromProjectURI": () => (/* reexport safe */ _factory_utils__WEBPACK_IMPORTED_MODULE_1__.fromProjectURI),
/* harmony export */   "serializeWorkflow": () => (/* reexport safe */ _factory_utils__WEBPACK_IMPORTED_MODULE_1__.serializeWorkflow),
/* harmony export */   "toLayerTreeData": () => (/* reexport safe */ _factory_utils__WEBPACK_IMPORTED_MODULE_1__.toLayerTreeData),
/* harmony export */   "toProjectData": () => (/* reexport safe */ _factory_utils__WEBPACK_IMPORTED_MODULE_1__.toProjectData),
/* harmony export */   "toProjectURI": () => (/* reexport safe */ _factory_utils__WEBPACK_IMPORTED_MODULE_1__.toProjectURI),
/* harmony export */   "AppObservables": () => (/* reexport safe */ _app_observables_service__WEBPACK_IMPORTED_MODULE_2__.AppObservables),
/* harmony export */   "AppBuildViewObservables": () => (/* reexport safe */ _observables_plotters__WEBPACK_IMPORTED_MODULE_3__.AppBuildViewObservables),
/* harmony export */   "AppStore": () => (/* reexport safe */ _app_store__WEBPACK_IMPORTED_MODULE_4__.AppStore),
/* harmony export */   "UiState": () => (/* reexport safe */ _app_store__WEBPACK_IMPORTED_MODULE_4__.UiState),
/* harmony export */   "addAdaptor": () => (/* reexport safe */ _app_store_connections__WEBPACK_IMPORTED_MODULE_5__.addAdaptor),
/* harmony export */   "addConnection": () => (/* reexport safe */ _app_store_connections__WEBPACK_IMPORTED_MODULE_5__.addConnection),
/* harmony export */   "deleteAdaptor": () => (/* reexport safe */ _app_store_connections__WEBPACK_IMPORTED_MODULE_5__.deleteAdaptor),
/* harmony export */   "deleteConnection": () => (/* reexport safe */ _app_store_connections__WEBPACK_IMPORTED_MODULE_5__.deleteConnection),
/* harmony export */   "setConnectionView": () => (/* reexport safe */ _app_store_connections__WEBPACK_IMPORTED_MODULE_5__.setConnectionView),
/* harmony export */   "subscribeConnections": () => (/* reexport safe */ _app_store_connections__WEBPACK_IMPORTED_MODULE_5__.subscribeConnections),
/* harmony export */   "updateAdaptor": () => (/* reexport safe */ _app_store_connections__WEBPACK_IMPORTED_MODULE_5__.updateAdaptor),
/* harmony export */   "addDescriptionBox": () => (/* reexport safe */ _app_store_description_box__WEBPACK_IMPORTED_MODULE_6__.addDescriptionBox),
/* harmony export */   "deleteDescriptionBox": () => (/* reexport safe */ _app_store_description_box__WEBPACK_IMPORTED_MODULE_6__.deleteDescriptionBox),
/* harmony export */   "updateDescriptionBox": () => (/* reexport safe */ _app_store_description_box__WEBPACK_IMPORTED_MODULE_6__.updateDescriptionBox),
/* harmony export */   "cleanChildrenLayers": () => (/* reexport safe */ _app_store_layer__WEBPACK_IMPORTED_MODULE_7__.cleanChildrenLayers),
/* harmony export */   "cloneLayerTree": () => (/* reexport safe */ _app_store_layer__WEBPACK_IMPORTED_MODULE_7__.cloneLayerTree),
/* harmony export */   "createLayer": () => (/* reexport safe */ _app_store_layer__WEBPACK_IMPORTED_MODULE_7__.createLayer),
/* harmony export */   "getLayer": () => (/* reexport safe */ _app_store_layer__WEBPACK_IMPORTED_MODULE_7__.getLayer),
/* harmony export */   "addModule": () => (/* reexport safe */ _app_store_modules__WEBPACK_IMPORTED_MODULE_8__.addModule),
/* harmony export */   "alignH": () => (/* reexport safe */ _app_store_modules__WEBPACK_IMPORTED_MODULE_8__.alignH),
/* harmony export */   "alignV": () => (/* reexport safe */ _app_store_modules__WEBPACK_IMPORTED_MODULE_8__.alignV),
/* harmony export */   "defaultModuleRendering": () => (/* reexport safe */ _app_store_modules__WEBPACK_IMPORTED_MODULE_8__.defaultModuleRendering),
/* harmony export */   "deleteModules": () => (/* reexport safe */ _app_store_modules__WEBPACK_IMPORTED_MODULE_8__.deleteModules),
/* harmony export */   "duplicateModules": () => (/* reexport safe */ _app_store_modules__WEBPACK_IMPORTED_MODULE_8__.duplicateModules),
/* harmony export */   "isGroupingModule": () => (/* reexport safe */ _app_store_modules__WEBPACK_IMPORTED_MODULE_8__.isGroupingModule),
/* harmony export */   "moveModules": () => (/* reexport safe */ _app_store_modules__WEBPACK_IMPORTED_MODULE_8__.moveModules),
/* harmony export */   "updateModule": () => (/* reexport safe */ _app_store_modules__WEBPACK_IMPORTED_MODULE_8__.updateModule),
/* harmony export */   "getDisplayedModulesView": () => (/* reexport safe */ _app_store_modules_group__WEBPACK_IMPORTED_MODULE_9__.getDisplayedModulesView),
/* harmony export */   "addPlugin": () => (/* reexport safe */ _app_store_plugins__WEBPACK_IMPORTED_MODULE_10__.addPlugin),
/* harmony export */   "getAvailablePlugins": () => (/* reexport safe */ _app_store_plugins__WEBPACK_IMPORTED_MODULE_10__.getAvailablePlugins),
/* harmony export */   "getPlugins": () => (/* reexport safe */ _app_store_plugins__WEBPACK_IMPORTED_MODULE_10__.getPlugins),
/* harmony export */   "setRenderingLayout": () => (/* reexport safe */ _app_store_runner_rendering__WEBPACK_IMPORTED_MODULE_11__.setRenderingLayout),
/* harmony export */   "setRenderingStyle": () => (/* reexport safe */ _app_store_runner_rendering__WEBPACK_IMPORTED_MODULE_11__.setRenderingStyle),
/* harmony export */   "CodeEditor": () => (/* reexport safe */ _code_editor_broadcast__WEBPACK_IMPORTED_MODULE_12__.CodeEditor),
/* harmony export */   "packageAssetComponent": () => (/* reexport safe */ _utils__WEBPACK_IMPORTED_MODULE_13__.packageAssetComponent),
/* harmony export */   "packageAssetProject": () => (/* reexport safe */ _utils__WEBPACK_IMPORTED_MODULE_13__.packageAssetProject),
/* harmony export */   "plugBuilderViewsSignals": () => (/* reexport safe */ _utils__WEBPACK_IMPORTED_MODULE_13__.plugBuilderViewsSignals),
/* harmony export */   "uuidv4": () => (/* reexport safe */ _utils__WEBPACK_IMPORTED_MODULE_13__.uuidv4),
/* harmony export */   "BuilderStateAPI": () => (/* reexport safe */ _extension__WEBPACK_IMPORTED_MODULE_14__.BuilderStateAPI)
/* harmony export */ });
/* harmony import */ var _app_debug_environment__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./app-debug.environment */ "./builder-editor/builder-state/app-debug.environment.ts");
/* harmony import */ var _factory_utils__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./factory-utils */ "./builder-editor/builder-state/factory-utils.ts");
/* harmony import */ var _app_observables_service__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./app-observables.service */ "./builder-editor/builder-state/app-observables.service.ts");
/* harmony import */ var _observables_plotters__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./observables-plotters */ "./builder-editor/builder-state/observables-plotters.ts");
/* harmony import */ var _app_store__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./app-store */ "./builder-editor/builder-state/app-store.ts");
/* harmony import */ var _app_store_connections__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./app-store-connections */ "./builder-editor/builder-state/app-store-connections.ts");
/* harmony import */ var _app_store_description_box__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! ./app-store-description-box */ "./builder-editor/builder-state/app-store-description-box.ts");
/* harmony import */ var _app_store_layer__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! ./app-store-layer */ "./builder-editor/builder-state/app-store-layer.ts");
/* harmony import */ var _app_store_modules__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(/*! ./app-store-modules */ "./builder-editor/builder-state/app-store-modules.ts");
/* harmony import */ var _app_store_modules_group__WEBPACK_IMPORTED_MODULE_9__ = __webpack_require__(/*! ./app-store-modules-group */ "./builder-editor/builder-state/app-store-modules-group.ts");
/* harmony import */ var _app_store_plugins__WEBPACK_IMPORTED_MODULE_10__ = __webpack_require__(/*! ./app-store-plugins */ "./builder-editor/builder-state/app-store-plugins.ts");
/* harmony import */ var _app_store_runner_rendering__WEBPACK_IMPORTED_MODULE_11__ = __webpack_require__(/*! ./app-store-runner-rendering */ "./builder-editor/builder-state/app-store-runner-rendering.ts");
/* harmony import */ var _code_editor_broadcast__WEBPACK_IMPORTED_MODULE_12__ = __webpack_require__(/*! ./code-editor-broadcast */ "./builder-editor/builder-state/code-editor-broadcast.ts");
/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_13__ = __webpack_require__(/*! ./utils */ "./builder-editor/builder-state/utils.ts");
/* harmony import */ var _extension__WEBPACK_IMPORTED_MODULE_14__ = __webpack_require__(/*! ./extension */ "./builder-editor/builder-state/extension.ts");

















/***/ }),

/***/ "./builder-editor/builder-state/observables-plotters.ts":
/*!**************************************************************!*\
  !*** ./builder-editor/builder-state/observables-plotters.ts ***!
  \**************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "AppBuildViewObservables": () => (/* binding */ AppBuildViewObservables)
/* harmony export */ });
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./app-debug.environment */ "./builder-editor/builder-state/app-debug.environment.ts");


class AppBuildViewObservables {
    constructor() {
        this.debugSingleton = _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__.AppDebugEnvironment.getInstance();
        this.connectionsView$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.modulesViewUpdated$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.moduleViewSelected$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.modulesDrawn$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.ReplaySubject(1);
        this.connectionsDrawn$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.ReplaySubject(1);
        this.descriptionsBoxesDrawn$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.ReplaySubject(1);
        this.activeLayerDrawn$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.ReplaySubject(1);
        this.modulesViewCompleted$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.plugsViewCompleted$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.connectionsViewCompleted$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.moduleEvent$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.moduleSelected$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.plugInputClicked$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.plugOutputClicked$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.mouseMoved$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.Subject();
        this.notification$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.ReplaySubject(1);
        if (this.debugSingleton.debugOn) {
            ["modulesViewUpdated$", "moduleViewSelected$", "moduleSelected$", "moduleEvent$", "modulesDrawn$",
                "descriptionsBoxesDrawn$", "activeLayerDrawn$", "notification$", "connectionsDrawn$"]
                .forEach(id => this[id].subscribe((...args) => this.log(id, ...args)));
        }
    }
    static getInstance() {
        if (!AppBuildViewObservables.instance)
            AppBuildViewObservables.instance = new AppBuildViewObservables();
        return AppBuildViewObservables.instance;
    }
    log(name, ...args) {
        this.debugSingleton.debugOn &&
            this.debugSingleton.logWorkflowView$({
                level: _app_debug_environment__WEBPACK_IMPORTED_MODULE_1__.LogLevel.Info,
                message: name,
                object: { args: args
                }
            });
    }
}
AppBuildViewObservables.instance = undefined;


/***/ }),

/***/ "./builder-editor/builder-state/project-delta.ts":
/*!*******************************************************!*\
  !*** ./builder-editor/builder-state/project-delta.ts ***!
  \*******************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "getDelta": () => (/* binding */ getDelta),
/* harmony export */   "workflowDelta": () => (/* binding */ workflowDelta)
/* harmony export */ });
function getDelta(oldCollection, newCollection) {
    let createdElements = newCollection.filter(x => !oldCollection.includes(x));
    let removedElements = oldCollection.filter(x => !newCollection.includes(x));
    return { createdElements, removedElements };
}
function workflowDelta(oldWf, newWf) {
    let diffsConnection = { createdElements: [], removedElements: [] };
    let diffModules = { createdElements: [], removedElements: [] };
    if (newWf.connections !== oldWf.connections) {
        let diffs = getDelta(oldWf.connections, newWf.connections);
        diffsConnection.createdElements.push(...diffs.createdElements);
        diffsConnection.removedElements.push(...diffs.removedElements);
    }
    if (newWf.modules !== oldWf.modules) {
        let diffs = getDelta(oldWf.modules, newWf.modules);
        diffModules.createdElements.push(...diffs.createdElements);
        diffModules.removedElements.push(...diffs.removedElements);
        let createdMdlesId = diffs.createdElements.map(m => m.moduleId);
        let deletedMdlesId = diffs.removedElements.map(m => m.moduleId);
        diffsConnection.createdElements.push(...newWf.connections.filter(c => createdMdlesId.includes(c.end.moduleId)), ...newWf.connections.filter(c => createdMdlesId.includes(c.start.moduleId)));
        diffsConnection.removedElements.push(...oldWf.connections.filter(c => deletedMdlesId.includes(c.start.moduleId) || deletedMdlesId.includes(c.end.moduleId)));
    }
    if (newWf.plugins !== oldWf.plugins) {
        let diffs = getDelta(oldWf.plugins, newWf.plugins);
        diffModules.createdElements.push(...diffs.createdElements);
        diffModules.removedElements.push(...diffs.removedElements);
        let createdMdlesId = diffs.createdElements.map(m => m.moduleId);
        let deletedMdlesId = diffs.removedElements.map(m => m.moduleId);
        diffsConnection.createdElements.push(...newWf.connections.filter(c => createdMdlesId.includes(c.end.moduleId)), ...newWf.connections.filter(c => createdMdlesId.includes(c.start.moduleId)));
        diffsConnection.removedElements.push(...oldWf.connections.filter(c => deletedMdlesId.includes(c.start.moduleId) || deletedMdlesId.includes(c.end.moduleId)));
    }
    diffsConnection.createdElements = Array.from(new Set(diffsConnection.createdElements));
    diffsConnection.removedElements = Array.from(new Set(diffsConnection.removedElements));
    diffModules.createdElements = Array.from(new Set(diffModules.createdElements));
    diffModules.removedElements = Array.from(new Set(diffModules.removedElements));
    return { connections: diffsConnection, modules: diffModules };
}


/***/ }),

/***/ "./builder-editor/builder-state/utils.ts":
/*!***********************************************!*\
  !*** ./builder-editor/builder-state/utils.ts ***!
  \***********************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "uuidv4": () => (/* binding */ uuidv4),
/* harmony export */   "packageAssetComponent": () => (/* binding */ packageAssetComponent),
/* harmony export */   "packageAssetProject": () => (/* binding */ packageAssetProject),
/* harmony export */   "plugBuilderViewsSignals": () => (/* binding */ plugBuilderViewsSignals)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var _factory_utils__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./factory-utils */ "./builder-editor/builder-state/factory-utils.ts");



function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}
function css(el, doc) {
    var sheets = doc.styleSheets, ret = [];
    el.matches = el.matches || el.webkitMatchesSelector || el.mozMatchesSelector
        || el.msMatchesSelector || el.oMatchesSelector;
    for (var i in sheets) {
        var rules = sheets[i].rules || sheets[i].cssRules;
        for (var r in rules) {
            if (el.matches(rules[r]["selectorText"])) {
                ret.push(rules[r].cssText);
            }
        }
    }
    return ret;
}
function packageAssetComponent(component, project) {
    let allModules = [component, ...component.getAllChildren()];
    let modules = allModules.filter(m => !(m instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.PluginFlux));
    let moduleIds = modules.map(m => m.moduleId);
    let plugins = project.workflow.plugins.filter(m => moduleIds.includes(m.parentModule.moduleId));
    let connections = component.getConnections();
    let layer = component.getLayerTree();
    let workflow = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Workflow(modules, connections.internals, plugins, layer);
    let fluxPacks = new Set(allModules.map(m => m.Factory.packId));
    let builderRendering = {
        modulesView: moduleIds.map(mdleId => project.builderRendering.modulesView.find(mView => mView.moduleId == mdleId)),
        connectionsView: connections.internals.map(cId => project.builderRendering.connectionsView.find(c => c.connectionId == cId))
            .filter(c => c)
    };
    let contentHtml = document.createElement('div');
    contentHtml.innerHTML = project.runnerRendering.layout;
    let componentHtml = contentHtml.querySelector("#" + component.moduleId);
    if (!componentHtml /*component instanceof GroupModules.Module*/)
        return {
            componentId: component.moduleId,
            workflow: (0,_factory_utils__WEBPACK_IMPORTED_MODULE_2__.serializeWorkflow)(workflow),
            builderRendering,
            fluxPacks: new Array(...fluxPacks),
        };
    let innerHtml = componentHtml ? componentHtml.outerHTML : "";
    let root = window["youwol"].renderView.document.querySelector("#" + component.moduleId);
    var all = root.getElementsByTagName('*');
    let divs = [root];
    for (var i = -1, l = all.length; ++i < l;) {
        divs.push(all[i]);
    }
    let cssItems = new Set(divs
        .filter(el => el.matches)
        .map(el => css(el, window["youwol"].renderView.document))
        .reduce((acc, e) => acc.concat(e), [])
        .filter(e => e[0] == "#" || e[0] == "."));
    return {
        componentId: component.moduleId,
        workflow: (0,_factory_utils__WEBPACK_IMPORTED_MODULE_2__.serializeWorkflow)(workflow),
        builderRendering,
        fluxPacks: new Array(...fluxPacks),
        runnerRendering: { layout: innerHtml, style: [...cssItems].reduce((acc, e) => acc + " " + e, "") }
    };
}
function packageAssetProject(project) {
    let publishRequest = {
        asset: {
            name: project.name,
            description: project.description
        },
        project: (0,_factory_utils__WEBPACK_IMPORTED_MODULE_2__.toProjectData)(project)
    };
    return publishRequest;
}
function plugBuilderViewsSignals(modules, actions, redirections$) {
    modules.forEach(mdle => {
        // This should go somewhere else above at some point (when multiple FluxAppstore data will be needed) 
        if (!mdle.Factory.consumersData.FluxAppstore)
            mdle.Factory.consumersData.FluxAppstore = { notifiersPluged: false };
        // notifier is static, we subscribe only one time to it
        if (mdle.Factory.BuilderView.notifier$ && !mdle.Factory.consumersData.FluxAppstore.notifiersPluged) {
            mdle.Factory.BuilderView.notifier$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_1__.filter)((event) => event.type == "configurationUpdated"))
                .subscribe((event) => {
                actions[event.type] && actions[event.type](event.data);
            });
            mdle.Factory.BuilderView.notifier$.subscribe(d => redirections$.next(d));
            mdle.Factory.consumersData.FluxAppstore.notifiersPluged = true;
        }
    });
}


/***/ }),

/***/ "./builder-editor/commands.ts":
/*!************************************!*\
  !*** ./builder-editor/commands.ts ***!
  \************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "commandsBuilder": () => (/* binding */ commandsBuilder)
/* harmony export */ });
function commandsBuilder() {
    function changeActiveBttnsState(selection, i = undefined) {
        /* when trigering command programatically, the button associated is not toggled, this is
        the purpose of this method. It is likely that something better exist in grapesjs */
        let elements = document.querySelectorAll(selection);
        let selectionClasses = ["gjs-pn-active", "gjs-four-color"];
        elements.forEach(e => e.classList.remove(...selectionClasses));
        if (i != undefined)
            elements[i].classList.add(...selectionClasses);
    }
    return [
        ['show-attributes', {
                run(editor, sender) {
                    const lmEl = document.getElementById("attributes-panel");
                    changeActiveBttnsState("#panel__builder-managers-actions .gjs-pn-btn", 0);
                    if (lmEl)
                        lmEl.classList.remove("d-none");
                },
                stop(editor, sender) {
                    const lmEl = document.getElementById("attributes-panel");
                    changeActiveBttnsState("#panel__builder-managers-actions .gjs-pn-btn");
                    if (lmEl)
                        lmEl.classList.add("d-none");
                },
            }],
        ['show-hide-panels', {
                run(editor, sender) {
                    document.getElementById("panels-container-builder").classList.add("collapsed");
                    let panel = document.getElementById("panel__right_builder");
                    panel.classList.add("collapsed");
                    panel.querySelectorAll(".flex-align-switch").forEach((e) => e.style.flexDirection = "column");
                    let buttons = panel.querySelector(".buttons-toolbox>.gjs-pn-buttons");
                    buttons.style.flexDirection = "column";
                },
                stop(editor, sender) {
                    document.getElementById("panels-container-builder").classList.remove("collapsed");
                    let panel = document.getElementById("panel__right_builder");
                    panel.classList.remove("collapsed");
                    panel.querySelectorAll(".flex-align-switch").forEach((e) => e.style.flexDirection = "row");
                    panel.querySelectorAll(".buttons-toolbox");
                    let buttons = panel.querySelector(".buttons-toolbox>.gjs-pn-buttons");
                    buttons.style.flexDirection = "row";
                },
            }]
    ];
}


/***/ }),

/***/ "./builder-editor/context-menu/context-menu.ts":
/*!*****************************************************!*\
  !*** ./builder-editor/context-menu/context-menu.ts ***!
  \*****************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "ContextMenuState": () => (/* binding */ ContextMenuState)
/* harmony export */ });
/* harmony import */ var _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/fv-tree */ "@youwol/fv-tree");
/* harmony import */ var _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _youwol_fv_context_menu__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @youwol/fv-context-menu */ "@youwol/fv-context-menu");
/* harmony import */ var _youwol_fv_context_menu__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_context_menu__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_3__);
/* harmony import */ var _nodes__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./nodes */ "./builder-editor/context-menu/nodes.ts");





let ALL_ACTIONS = {
    newModules: {
        createNode: () => new _nodes__WEBPACK_IMPORTED_MODULE_4__.NewModulesNode(),
        applicable: (state) => state.getModulesSelected().length >= 0
    },
    addPlugins: {
        createNode: () => new _nodes__WEBPACK_IMPORTED_MODULE_4__.AddPluginsNode(),
        applicable: (state) => state.getModulesSelected().length == 1
    },
    journals: {
        createNode: () => new _nodes__WEBPACK_IMPORTED_MODULE_4__.JournalsNode(),
        applicable: (state) => {
            return state.getModulesSelected().length == 1 &&
                state.getModuleSelected().journals.length > 0;
        }
    },
};
class ContextMenuState extends _youwol_fv_context_menu__WEBPACK_IMPORTED_MODULE_1__.ContextMenu.State {
    constructor(appState, drawingArea) {
        super((0,rxjs__WEBPACK_IMPORTED_MODULE_2__.fromEvent)(drawingArea.parentDiv, 'contextmenu').pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_3__.tap)((ev) => ev.preventDefault())));
        this.appState = appState;
        this.drawingArea = drawingArea;
        this.htmlElement = drawingArea.parentDiv;
    }
    dispatch(ev) {
        let children = Object.values(ALL_ACTIONS)
            .filter(action => action.applicable(this.appState))
            .map(action => action.createNode());
        let root = new _nodes__WEBPACK_IMPORTED_MODULE_4__.ContextRootNode({ children });
        let state = new ContextTreeState(root);
        let view = new _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0__.ImmutableTree.View({
            state,
            headerView,
            class: "fv-bg-background fv-text-primary p-2 rounded"
        });
        state.selectedNode$.next(root);
        state.selectedNode$.subscribe((node) => node.execute(this, { event: ev }));
        return view;
    }
}
class ContextTreeState extends _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0__.ImmutableTree.State {
    constructor(root) {
        super({ rootNode: root, expandedNodes: [root.id] });
    }
}
function headerView(state, node) {
    return {
        class: 'd-flex w-100 align-items-baseline fv-pointer fv-hover-bg-background-alt px-1',
        children: [
            { tag: 'i', class: node.faIcon },
            { tag: 'span', class: 'mx-2 w-100', innerText: node.name, style: { 'user-select': 'none' } }
        ]
    };
}


/***/ }),

/***/ "./builder-editor/context-menu/index.ts":
/*!**********************************************!*\
  !*** ./builder-editor/context-menu/index.ts ***!
  \**********************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "ContextMenuState": () => (/* reexport safe */ _context_menu__WEBPACK_IMPORTED_MODULE_0__.ContextMenuState),
/* harmony export */   "AddPluginsNode": () => (/* reexport safe */ _nodes__WEBPACK_IMPORTED_MODULE_1__.AddPluginsNode),
/* harmony export */   "ContextRootNode": () => (/* reexport safe */ _nodes__WEBPACK_IMPORTED_MODULE_1__.ContextRootNode),
/* harmony export */   "ContextTreeNode": () => (/* reexport safe */ _nodes__WEBPACK_IMPORTED_MODULE_1__.ContextTreeNode),
/* harmony export */   "JournalsNode": () => (/* reexport safe */ _nodes__WEBPACK_IMPORTED_MODULE_1__.JournalsNode),
/* harmony export */   "NewModulesNode": () => (/* reexport safe */ _nodes__WEBPACK_IMPORTED_MODULE_1__.NewModulesNode)
/* harmony export */ });
/* harmony import */ var _context_menu__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./context-menu */ "./builder-editor/context-menu/context-menu.ts");
/* harmony import */ var _nodes__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./nodes */ "./builder-editor/context-menu/nodes.ts");




/***/ }),

/***/ "./builder-editor/context-menu/nodes.ts":
/*!**********************************************!*\
  !*** ./builder-editor/context-menu/nodes.ts ***!
  \**********************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "ContextTreeNode": () => (/* binding */ ContextTreeNode),
/* harmony export */   "ContextRootNode": () => (/* binding */ ContextRootNode),
/* harmony export */   "NewModulesNode": () => (/* binding */ NewModulesNode),
/* harmony export */   "AddPluginsNode": () => (/* binding */ AddPluginsNode),
/* harmony export */   "JournalsNode": () => (/* binding */ JournalsNode)
/* harmony export */ });
/* harmony import */ var _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/fv-tree */ "@youwol/fv-tree");
/* harmony import */ var _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _views_import_modules_view__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ../views/import-modules.view */ "./builder-editor/views/import-modules.view.ts");
/* harmony import */ var _views_journals_view__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ../views/journals.view */ "./builder-editor/views/journals.view.ts");



class ContextTreeNode extends _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0__.ImmutableTree.Node {
    constructor({ id, children, name, faIcon }) {
        super({ id, children });
        this.name = name;
        this.faIcon = faIcon;
    }
    execute(state, { event }) { }
}
class ContextRootNode extends ContextTreeNode {
    constructor({ children }) {
        super({ id: 'root', children, name: 'menu list', faIcon: '' });
    }
}
class NewModulesNode extends ContextTreeNode {
    constructor() {
        super({ id: 'new-modules', children: undefined, name: 'new module(s)', faIcon: 'fas fa-microchip' });
    }
    execute(state, { event }) {
        let worldCoordinates = state.drawingArea.invert(event.clientX, event.clientY);
        _views_import_modules_view__WEBPACK_IMPORTED_MODULE_1__.ImportModulesView.popupModal(state.appState, (nodes) => {
            let libraries = nodes.map(node => node.library);
            let fluxPacks = nodes.flatMap(node => node.fluxPacks.map(fluxPack => fluxPack));
            state.appState.addLibraries$(libraries, fluxPacks).subscribe(() => {
                nodes.forEach(node => state.appState.addModule(node.factory, worldCoordinates));
            });
        });
    }
}
class AddPluginsNode extends ContextTreeNode {
    constructor() {
        super({ id: 'add-plugins', children: undefined, name: 'add plugin(s)', faIcon: 'fas fa-microchip' });
    }
    execute(state, { event }) {
        _views_import_modules_view__WEBPACK_IMPORTED_MODULE_1__.ImportModulesView.popupModal(state.appState, (nodes) => {
            let parentModule = state.appState.getModuleSelected();
            let libraries = nodes.map(node => node.library);
            let fluxPacks = nodes.flatMap(node => node.fluxPacks.map(fluxPack => fluxPack));
            state.appState.addLibraries$(libraries, fluxPacks).subscribe(() => {
                nodes.forEach(node => state.appState.addPlugin(node.factory, parentModule));
            });
        });
    }
}
class JournalsNode extends ContextTreeNode {
    constructor() {
        super({ id: 'journals', children: undefined, name: 'journals', faIcon: 'fas fa-newspaper' });
    }
    execute(state) {
        let module = state.appState.getModuleSelected();
        _views_journals_view__WEBPACK_IMPORTED_MODULE_2__.JournalsView.popupModal({ module });
    }
}


/***/ }),

/***/ "./builder-editor/drawing-utils.ts":
/*!*****************************************!*\
  !*** ./builder-editor/drawing-utils.ts ***!
  \*****************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "getConnections$": () => (/* binding */ getConnections$),
/* harmony export */   "convert": () => (/* binding */ convert),
/* harmony export */   "getBoundingBox": () => (/* binding */ getBoundingBox)
/* harmony export */ });
function getConnections$(connectionsUpdated$) {
    /*let maping = ( c : Connection) => ({
        //data: { input : c.end, output: c.start},
        data: c,
        classes : ["connection"], id: c.end.moduleId+"-"+c.start.moduleId,
        selector1 : "g#"+ c.end.moduleId + "-"+c.end.slotId+".plug.input."+c.end.moduleId+" circle",
        x1:  (element) : number => Number(element.getAttribute("x1")),
        y1:  (element) : number => Number(element.getAttribute("y1")),
        selector2 : "g#"+ c.start.moduleId + "-"+c.start.slotId+".plug.output."+c.start.moduleId+" circle",
        x2: (element) : number=> Number(element.getAttribute("x2")),
        y2: (element)  : number=> Number(element.getAttribute("y2")),
    })

    return connectionsUpdated$.pipe(
        operators.map( (connections:Array<Connection>) =>
            connections.reduce( (acc: any, c:Connection) => acc.concat( maping(c) ),[] ))
    )*/
}
function convert(bbox, matrix, drawingArea) {
    var offset = document.getElementById(drawingArea.svgCanvas.attr("id")).getBoundingClientRect();
    let transform = drawingArea.overallTranform;
    let a = {
        xmin: ((matrix.a * bbox.x) + (matrix.c * bbox.y) + matrix.e - offset.left
            - transform.translateX) / transform.scale,
        ymin: ((matrix.b * bbox.x) + (matrix.d * bbox.y) + matrix.f - offset.top
            - transform.translateY) / transform.scale,
        xmax: ((matrix.a * (bbox.x + bbox.width)) + (matrix.c * (bbox.y + bbox.height)) + matrix.e - offset.left
            - transform.translateX) / transform.scale,
        ymax: ((matrix.b * (bbox.x + bbox.width)) + (matrix.d * (bbox.y + bbox.height)) + matrix.f - offset.top
            - transform.translateY) / transform.scale
    };
    return a;
}
function getBoundingBox(modulesId, margin, drawingArea) {
    let bbox = modulesId
        .map((mid) => document.getElementById(mid))
        .filter(e => e)
        .map((e) => convert(e.getBBox(), e.getScreenCTM(), drawingArea))
        .reduce((acc, e) => ({
        xmin: Math.min(acc.xmin, e.xmin), xmax: Math.max(acc.xmax, e.xmax),
        ymin: Math.min(acc.ymin, e.ymin), ymax: Math.max(acc.ymax, e.ymax)
    }), { xmin: 1e6, xmax: -1e6, ymin: 1e6, ymax: 1e-6 });
    return { x: bbox.xmin - margin,
        y: bbox.ymin - margin,
        width: bbox.xmax - bbox.xmin + 2 * margin,
        height: bbox.ymax - bbox.ymin + 2 * margin };
}


/***/ }),

/***/ "./builder-editor/index.ts":
/*!*********************************!*\
  !*** ./builder-editor/index.ts ***!
  \*********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "AddPluginsNode": () => (/* reexport safe */ _context_menu_index__WEBPACK_IMPORTED_MODULE_0__.AddPluginsNode),
/* harmony export */   "ContextMenuState": () => (/* reexport safe */ _context_menu_index__WEBPACK_IMPORTED_MODULE_0__.ContextMenuState),
/* harmony export */   "ContextRootNode": () => (/* reexport safe */ _context_menu_index__WEBPACK_IMPORTED_MODULE_0__.ContextRootNode),
/* harmony export */   "ContextTreeNode": () => (/* reexport safe */ _context_menu_index__WEBPACK_IMPORTED_MODULE_0__.ContextTreeNode),
/* harmony export */   "JournalsNode": () => (/* reexport safe */ _context_menu_index__WEBPACK_IMPORTED_MODULE_0__.JournalsNode),
/* harmony export */   "NewModulesNode": () => (/* reexport safe */ _context_menu_index__WEBPACK_IMPORTED_MODULE_0__.NewModulesNode),
/* harmony export */   "AdaptorEditoView": () => (/* reexport safe */ _views_index__WEBPACK_IMPORTED_MODULE_1__.AdaptorEditoView),
/* harmony export */   "AssetsExplorerView": () => (/* reexport safe */ _views_index__WEBPACK_IMPORTED_MODULE_1__.AssetsExplorerView),
/* harmony export */   "CodeEditorView": () => (/* reexport safe */ _views_index__WEBPACK_IMPORTED_MODULE_1__.CodeEditorView),
/* harmony export */   "CodePropertyEditorView": () => (/* reexport safe */ _views_index__WEBPACK_IMPORTED_MODULE_1__.CodePropertyEditorView),
/* harmony export */   "ConfigurationStatusView": () => (/* reexport safe */ _views_index__WEBPACK_IMPORTED_MODULE_1__.ConfigurationStatusView),
/* harmony export */   "ContextView": () => (/* reexport safe */ _views_index__WEBPACK_IMPORTED_MODULE_1__.ContextView),
/* harmony export */   "DataTreeView": () => (/* reexport safe */ _views_index__WEBPACK_IMPORTED_MODULE_1__.DataTreeView),
/* harmony export */   "ExpectationView": () => (/* reexport safe */ _views_index__WEBPACK_IMPORTED_MODULE_1__.ExpectationView),
/* harmony export */   "ImportModulesView": () => (/* reexport safe */ _views_index__WEBPACK_IMPORTED_MODULE_1__.ImportModulesView),
/* harmony export */   "InputStatusView": () => (/* reexport safe */ _views_index__WEBPACK_IMPORTED_MODULE_1__.InputStatusView),
/* harmony export */   "ShareUriView": () => (/* reexport safe */ _views_index__WEBPACK_IMPORTED_MODULE_1__.ShareUriView),
/* harmony export */   "infoView": () => (/* reexport safe */ _views_index__WEBPACK_IMPORTED_MODULE_1__.infoView),
/* harmony export */   "commandsBuilder": () => (/* reexport safe */ _commands__WEBPACK_IMPORTED_MODULE_2__.commandsBuilder),
/* harmony export */   "convert": () => (/* reexport safe */ _drawing_utils__WEBPACK_IMPORTED_MODULE_3__.convert),
/* harmony export */   "getBoundingBox": () => (/* reexport safe */ _drawing_utils__WEBPACK_IMPORTED_MODULE_3__.getBoundingBox),
/* harmony export */   "getConnections$": () => (/* reexport safe */ _drawing_utils__WEBPACK_IMPORTED_MODULE_3__.getConnections$),
/* harmony export */   "ConnectionView": () => (/* reexport safe */ _panel_module_attributes__WEBPACK_IMPORTED_MODULE_4__.ConnectionView),
/* harmony export */   "createAttributesPanel": () => (/* reexport safe */ _panel_module_attributes__WEBPACK_IMPORTED_MODULE_4__.createAttributesPanel),
/* harmony export */   "createPart": () => (/* reexport safe */ _panel_suggestion__WEBPACK_IMPORTED_MODULE_5__.createPart),
/* harmony export */   "createSuggestionsPanel": () => (/* reexport safe */ _panel_suggestion__WEBPACK_IMPORTED_MODULE_5__.createSuggestionsPanel),
/* harmony export */   "getBuilderPanels": () => (/* reexport safe */ _panels__WEBPACK_IMPORTED_MODULE_6__.getBuilderPanels),
/* harmony export */   "grapesButton": () => (/* reexport safe */ _utils_view__WEBPACK_IMPORTED_MODULE_7__.grapesButton)
/* harmony export */ });
/* harmony import */ var _context_menu_index__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./context-menu/index */ "./builder-editor/context-menu/index.ts");
/* harmony import */ var _views_index__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./views/index */ "./builder-editor/views/index.ts");
/* harmony import */ var _commands__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./commands */ "./builder-editor/commands.ts");
/* harmony import */ var _drawing_utils__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./drawing-utils */ "./builder-editor/drawing-utils.ts");
/* harmony import */ var _panel_module_attributes__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./panel-module-attributes */ "./builder-editor/panel-module-attributes.ts");
/* harmony import */ var _panel_suggestion__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./panel-suggestion */ "./builder-editor/panel-suggestion.ts");
/* harmony import */ var _panels__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! ./panels */ "./builder-editor/panels.ts");
/* harmony import */ var _utils_view__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! ./utils.view */ "./builder-editor/utils.view.ts");










/***/ }),

/***/ "./builder-editor/panel-module-attributes.ts":
/*!***************************************************!*\
  !*** ./builder-editor/panel-module-attributes.ts ***!
  \***************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "ConnectionView": () => (/* binding */ ConnectionView),
/* harmony export */   "createAttributesPanel": () => (/* binding */ createAttributesPanel)
/* harmony export */ });
/* harmony import */ var tslib__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! tslib */ "../../node_modules/tslib/tslib.es6.js");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! @youwol/flux-svg-plots */ "@youwol/flux-svg-plots");
/* harmony import */ var _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! @youwol/flux-view */ "@youwol/flux-view");
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_view__WEBPACK_IMPORTED_MODULE_3__);
/* harmony import */ var _utils_view__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./utils.view */ "./builder-editor/utils.view.ts");
/* harmony import */ var _views_code_property_editor_view__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./views/code-property-editor.view */ "./builder-editor/views/code-property-editor.view.ts");
/* harmony import */ var _views_adaptor_editor_view__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! ./views/adaptor-editor.view */ "./builder-editor/views/adaptor-editor.view.ts");








let connection = {
    schemas: { ConnectionView: {} }
};
let ConnectionView = class ConnectionView {
    constructor(wireless = false, adaptor = `
return ({data,configuration,context}) => ({
    data: data,
    context:{},
    configuration: configuration
})`) {
        this.wireless = wireless;
        this.adaptor = adaptor;
    }
};
(0,tslib__WEBPACK_IMPORTED_MODULE_7__.__decorate)([
    (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.Property)({ description: "wireless" }),
    (0,tslib__WEBPACK_IMPORTED_MODULE_7__.__metadata)("design:type", Boolean)
], ConnectionView.prototype, "wireless", void 0);
(0,tslib__WEBPACK_IMPORTED_MODULE_7__.__decorate)([
    (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.Property)({ description: "adaptor", type: 'code' }),
    (0,tslib__WEBPACK_IMPORTED_MODULE_7__.__metadata)("design:type", String)
], ConnectionView.prototype, "adaptor", void 0);
ConnectionView = (0,tslib__WEBPACK_IMPORTED_MODULE_7__.__decorate)([
    (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.Schema)({
        pack: connection,
        description: "Intersection from ray casting"
    }),
    (0,tslib__WEBPACK_IMPORTED_MODULE_7__.__metadata)("design:paramtypes", [Object, String])
], ConnectionView);

function flattenPropertiesNative(schema, data, suffix, Factory) {
    let acc = { [suffix.slice(1)]: [schema, data] };
    if (schema && schema.extends && Factory) {
        let props = flattenPropertiesNative(Factory.schemas[schema.extends], data, suffix, Factory);
        _.merge(acc, props);
    }
    if (schema && schema.type && Factory && Factory.schemas && Factory.schemas[schema.type]) {
        let props = flattenPropertiesNative(Factory.schemas[schema.type], data, suffix, Factory);
        _.merge(acc, props);
    }
    if (schema && schema.attributes) {
        let props = Object.entries(schema.attributes).reduce((acc, [key, val]) => {
            return _.merge(acc, flattenPropertiesNative(val, data[key], `${suffix}.${key}`, Factory));
        }, {});
        _.merge(acc, props);
    }
    return Object.keys(acc)
        .filter(key => acc[key][0])
        .reduce((obj, key) => { obj[key] = acc[key]; return obj; }, {});
}
function moduleControls(d, appStore, panelDiv) {
    let flattened = (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.flattenSchemaWithValue)(d.configuration.data);
    let titleDiv = input("wf-config-title", "wf-config-title", "title", "", [{ type: "string" }, d.configuration.title]);
    let controls = Object.entries(flattened).slice(1)
        .map(([k, v]) => widgetsFactory(d, k, v, appStore))
        .filter((d) => d);
    let header = settingsHeader(d.Factory.resources, d.configuration, ({ title, description, data }) => appStore.updateModule(d, new d.Factory.Configuration({ title, description, data })), panelDiv);
    return [[titleDiv, ...controls], header];
}
function connectionControls(d, appStore, panelDiv) {
    let data = appStore.getConnectionView(d.connectionId) || new ConnectionView();
    if (d.adaptor) {
        data.adaptor = d.adaptor.toString();
    }
    let schema = {
        "attributes": {
            "wireless": {
                "type": "Boolean",
                "name": "wireless",
                "metadata": {
                    "description": "wireless"
                }
            },
            "adaptor": {
                "type": "String",
                "name": "adaptor",
                "metadata": {
                    "description": "adaptor",
                    "type": "code"
                }
            }
        },
        "methods": [],
        "extends": [
            ""
        ]
    };
    let flattened = flattenPropertiesNative(schema, data, "", undefined);
    let controls = Object.entries(flattened).slice(1)
        .map(([k, v]) => widgetsFactory(d, k, v, appStore))
        .filter((d) => d);
    let validationBtt = button({ data: data }, (properties) => {
        if (properties.data.adaptor) {
            let adaptor = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.Adaptor((0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.uuidv4)(), properties.data.adaptor);
            appStore.addAdaptor(adaptor, d);
        }
        appStore.setConnectionView(d, properties.data);
    }, panelDiv);
    return [[...controls], validationBtt];
}
function createAttributesPanel(appStore, appObservables) {
    (0,rxjs__WEBPACK_IMPORTED_MODULE_0__.merge)(appObservables.moduleSelected$, appObservables.connectionSelected$).subscribe((d) => {
        document.getElementById("attributes-panel").innerHTML = "";
        let panelDiv = document.getElementById("attributes-panel");
        var container = document.createDocumentFragment();
        let [attrControls, validationBtn] = d.moduleId ?
            moduleControls(d, appStore, panelDiv) :
            connectionControls(d, appStore, panelDiv);
        // All but the validation button
        panelDiv.appendChild(validationBtn);
        attrControls.forEach(div => container.appendChild(div));
        panelDiv.appendChild(container);
    });
    appObservables.unselect$.subscribe((_) => {
        document.getElementById("attributes-panel").innerHTML = "";
    });
    var container = document.createDocumentFragment();
    return container;
}
function widgetsFactory(mdle, key, value, appStore) {
    if (key === "code" || (value[0] && value[0].metadata && value[0].metadata.type && value[0].metadata.type.includes("code")))
        return code(mdle, (0,_youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_2__.toCssName)(key), "", key, key, value[1], value[0].metadata, appStore);
    if (value && value[0] && value[0].type && value[0].type.toLowerCase() == "boolean")
        return checkbox(mdle, (0,_youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_2__.toCssName)(key), key, key, value[1]);
    if (value && value[0] && value[0].type && value[0].type.toLowerCase() == "string" && value[0].metadata && value[0].metadata.enum)
        return options((0,_youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_2__.toCssName)(key), "", key, value[0].metadata.enum, key, value);
    if (value && value[0] && value[0].type && value[0].type.toLowerCase() == "string")
        return input((0,_youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_2__.toCssName)(key), "", key, key, value);
    if (value && value[0] && value[0].type && value[0].type.toLowerCase() == "number")
        return input((0,_youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_2__.toCssName)(key), "", key, key, value);
    return undefined;
}
function settingsHeader(resources, conf, callback, div) {
    let configData = _.cloneDeep(conf.data);
    let applyBtn = (0,_utils_view__WEBPACK_IMPORTED_MODULE_4__.grapesButton)({
        title: "apply",
        classes: 'fas fa-check',
        onclick: () => applySettings(conf, configData, callback, div)
    });
    let resourceExpanded$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.BehaviorSubject(false);
    let menuView = resources
        ? {
            class: 'w-100',
            style: { position: 'absolute' },
            children: Object.entries(resources).map(([name, url]) => {
                return (0,_utils_view__WEBPACK_IMPORTED_MODULE_4__.grapesButton)({
                    title: name,
                    classes: "",
                    onclick: () => { window.open(url, '_blank'); resourceExpanded$.next(false); }
                });
            })
        }
        : {};
    let selectResource = {
        class: 'flex-grow-1',
        style: { position: 'relative' },
        children: [
            { class: 'd-flex align-items-center gjs-pn-btn fv-text-focus',
                onclick: () => resourceExpanded$.next(!resourceExpanded$.getValue()),
                children: [
                    {
                        tag: 'i',
                        class: (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_3__.attr$)(resourceExpanded$, (expanded) => expanded ? 'fas fa-caret-down px-2' : 'fas fa-caret-right px-2')
                    },
                    {
                        tag: 'i',
                        class: 'fas fa-book-reader'
                    }
                ]
            },
            (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_3__.child$)(resourceExpanded$, (expanded) => expanded ? menuView : {})
        ]
    };
    let view = {
        class: "d-flex align-items-center p-2",
        style: { position: 'sticky', top: '0px', 'z-index': 5, 'background-color': "#444" },
        children: [
            applyBtn,
            resources ? selectResource : {}
        ]
    };
    return (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_3__.render)(view);
}
function applySettings(conf, configData, callback, div) {
    let titleDiv = div.querySelector("#wf-config-title input");
    let title = titleDiv ? titleDiv["value"] : undefined;
    div.querySelectorAll(".wf-config-property").forEach((inputDiv) => {
        let pathElems = inputDiv.getAttribute("path").split('.');
        let lastRed = pathElems.slice(0, -1).reduce((acc, elem) => acc[elem], configData);
        lastRed[pathElems.slice(-1)[0]] = inputDiv.value || inputDiv.getAttribute("value");
        if (inputDiv.type == "number")
            lastRed[pathElems.slice(-1)[0]] = Number(lastRed[pathElems.slice(-1)[0]]);
        if (inputDiv.type == "checkbox") {
            lastRed[pathElems.slice(-1)[0]] = inputDiv["checked"];
        }
        if (inputDiv.type == "select-one") {
            let v = inputDiv['options'][inputDiv['selectedIndex']].value;
            lastRed[pathElems.slice(-1)[0]] = v;
        }
    });
    document.querySelectorAll("span.modified").forEach(elem => elem.classList.toggle("modified"));
    callback({ title, description: conf.description, data: configData });
}
function button(conf, callback, div) {
    let configData = _.cloneDeep(conf.data);
    let bttDiv = document.createElement("div");
    bttDiv.style.position = 'sticky';
    bttDiv.style.top = "-5px";
    bttDiv.style.zIndex = "5";
    bttDiv.style.backgroundColor = "#444";
    bttDiv.onclick = () => {
        applySettings(conf, configData, callback, div);
    };
    bttDiv.innerHTML = `<span class="gjs-pn-btn gjs-pn-active fv-text-focus"> <i class="fas fa-check p-2 ">Apply settings</i></span>`;
    return bttDiv;
}
function input(id, classe, label, path, description) {
    let value = description[1];
    let type = description[0]["type"];
    function option({ label, value }) {
        return `<option value="${value}">${label}</option>`;
    }
    let innerHtml = `
    <div id="${id}" class="gjs-sm-property gjs-sm-select gjs-sm-property__${classe}" style="display: block;">
      <div class="gjs-sm-label gjs-four-color">        
        <span class="gjs-sm-icon " title="">${label}</span>
        <b class="gjs-sm-clear" data-clear-style="" style="display: none;">⨯</b>    
      </div>
      <div class="gjs-fields">        
        <div class="gjs-field gjs-select">
            <input path="${path}" type="${type}" class="wf-config-property" placeholder="${value}" value="${value}">
        </div>
      </div>
    </div>
    `;
    let div = document.createElement('div');
    div.innerHTML = innerHtml;
    return div;
}
function checkbox(id, classe, label, path, value) {
    let innerHtml = `
    <div id="${id}" class="d-flex py-1 gjs-sm-property gjs-sm-select gjs-sm-property__${classe}" style="display: block;">
      <div class="gjs-sm-label gjs-four-color">    
        <span class="gjs-sm-icon " title="">${label}</span>
        <input type="checkbox" path="${path}" name="${label}" class="wf-config-property mx-2" placeholder="${value}" ${value ? 'checked' : ''} value="${value}">  
      </div>
    </div>
    `;
    let div = document.createElement('div');
    div.innerHTML = innerHtml;
    return div;
}
function options(id, classe, label, options, path, value) {
    let innerHtml = `
    <div id="${id}" class="gjs-sm-property gjs-sm-select gjs-sm-property__${classe}" style="display: block;">
      <div class="gjs-sm-label">
        
      
      <b class="gjs-sm-clear" data-clear-style="" style="display: none;">⨯</b>
      ${label}
      </div>
      <div class="gjs-fields">
        
      <div class="gjs-field gjs-select">
        <span id="gjs-sm-input-holder">
        <select class="wf-config-property" path="${path}" type="select-one">
        ` +
        options.map(option => option == value[1] ? `<option value="${option}" selected>${option} </option>` : `<option value="${option}">${option} </option>`) +
        `</select>
        <div class="gjs-sel-arrow">
          <div class="gjs-d-s-arrow"></div>
        </div>
      </div>
    
      </div>
    </div>
    `;
    let div = document.createElement('div');
    div.innerHTML = innerHtml;
    return div;
}
/*

export class ExternalCode extends Code {

    constructor(
        public readonly ownerId: string,
        public readonly ownerName: string,
        public readonly content : string,
        public readonly type: CodeType,
        public readonly metadata: any = {}) {
        super(content,type, metadata )
    }
}
*/
function code(selection, id, classe, label, path, value, metadata, appStore) {
    let innerHtml = `
    <div id="${id}" class="gjs-sm-property gjs-sm-select gjs-sm-property__${classe}" style="display: block;">
      <div class="gjs-sm-label gjs-four-color">        
        <span class="gjs-sm-icon pr-2 wf-code-bttn-label wf-config-property" path="${path}" title="" >${label}</span> 
            <i class="fas fa-edit wf-code-bttn btn btn-secondary"></i>
        <b class="gjs-sm-clear" data-clear-style="" style="display: none;">⨯</b>    
      </div>
    </div>
    `;
    let div = document.createElement('div');
    div.innerHTML = innerHtml;
    let bttn = div.querySelector(".wf-code-bttn");
    let labelDiv = div.querySelector(".wf-code-bttn-label");
    labelDiv.setAttribute("value", value);
    let onUpdateMdle = (content) => {
        let pathElems = path.split('.');
        let mdle = selection;
        let lastRed = pathElems
            .slice(0, -1)
            .reduce((acc, elem) => acc[elem], mdle.configuration.data);
        lastRed[pathElems.slice(-1)[0]] = content;
        appStore.updateModule(mdle, mdle.configuration);
    };
    let onUpdateAdaptor = (content) => {
        let adaptor = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.Adaptor((0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.uuidv4)(), content);
        appStore.addAdaptor(adaptor, selection);
    };
    bttn.onclick = () => {
        if (selection instanceof (_youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.ModuleFlux)) {
            _views_code_property_editor_view__WEBPACK_IMPORTED_MODULE_5__.CodePropertyEditorView.popupModal({
                mdle: selection,
                initialCode: value,
                editorConfiguration: metadata.editorConfiguration,
                onUpdate: onUpdateMdle
            });
        }
        else {
            _views_adaptor_editor_view__WEBPACK_IMPORTED_MODULE_6__.AdaptorEditoView.popupModal({
                connection: selection,
                initialCode: value,
                appStore,
                onUpdate: onUpdateAdaptor
            });
        }
    };
    return div;
}
/*
function select(id: string, classe: string, label: string,  options: Array<{ label, value }>) : HTMLDivElement {

    function option({ label, value }) {
        return `<option value="${value}">${label}</option>`
    }
    let innerHtml=`
    <div id="${id}" class="gjs-sm-property gjs-sm-select gjs-sm-property__${classe}" style="display: block;">
      <div class="gjs-sm-label gjs-four-color">
        <span class="gjs-sm-icon " title="">
            ${label}
        </span>
      <b class="gjs-sm-clear" data-clear-style="" style="display: none;">⨯</b>
    
      </div>
      <div class="gjs-fields">
        <div class="gjs-field gjs-select">
            <span id="gjs-sm-input-holder">
                <select> ${ options.reduce((acc, e) => acc + option(e), "")} </select>
            </span>
            <div class="gjs-sel-arrow">
            <div class="gjs-d-s-arrow"></div>
            </div>
        </div>
      </div>
    </div>
    `
    let div = document.createElement('div') as HTMLDivElement
    div.innerHTML = innerHtml
    return div
}


function colorPicker(id : string, classe: string, label: string, defaultColor: string ) : HTMLDivElement{

    let innerHtml = `
    <div id="${id}" class="gjs-sm-property gjs-sm-color gjs-sm-property__${classe}" style="display: block;">
        <div class="gjs-sm-label gjs-four-color">
            <span class="gjs-sm-icon " title="">
                ${label}
            </span>
            <b class="gjs-sm-clear" data-clear-style="" style="display: none;">⨯</b>
            
        </div>
        <div class="gjs-fields">
                
            <div class="gjs-field gjs-field-color">
            <div class="gjs-input-holder"><input type="text" placeholder="none"></div>
            <div class="gjs-field-colorp">
                <div class="gjs-field-colorp-c" data-colorp-c="">
                <div class="gjs-checker-bg"></div>
                <div class="gjs-field-color-picker" style="background-color: ${defaultColor};"></div></div>
            </div>
            </div>
        </div>
    </div>
    `
    let div = document.createElement('div') as HTMLDivElement
    div.innerHTML = innerHtml
    return div
}

function intInput(id : string, classe: string, label: string, defaultValue: number ) : HTMLDivElement{

    let innerHtml = `
    <div id="${id}" class="gjs-sm-property gjs-sm-integer gjs-sm-property__${classe}" style="display: block;">
        <div class="gjs-sm-label">
            <span class="gjs-sm-icon " title="">
            ${label}
            </span>
        </div>
        <div class="gjs-fields">
            <div class="gjs-field gjs-field-integer">
                <span class="gjs-input-holder"><input type="text" placeholder="${defaultValue}"></span>
                <span class="gjs-field-units"></span>
                <div class="gjs-field-arrows" data-arrows="">
                    <div class="gjs-field-arrow-u" data-arrow-up=""></div>
                    <div class="gjs-field-arrow-d" data-arrow-down=""></div>
                </div>
            </div>
        </div>
    </div>`
    
    let div = document.createElement('div') as HTMLDivElement
    div.innerHTML = innerHtml
    return div
}
*/ 


/***/ }),

/***/ "./builder-editor/panel-suggestion.ts":
/*!********************************************!*\
  !*** ./builder-editor/panel-suggestion.ts ***!
  \********************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "createPart": () => (/* binding */ createPart),
/* harmony export */   "createSuggestionsPanel": () => (/* binding */ createSuggestionsPanel)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);

function createPart(title, classes) {
    let block = document.createElement("div");
    let titleDiv = document.createElement("div");
    let icon = document.createElement("i");
    let blockC = document.createElement("div");
    blockC.classList.add("gjs-blocks-c", "d-none", ...classes);
    titleDiv.classList.add("gjs-title");
    block.classList.add("gjs-block-category", "gjs-open");
    icon.classList.add("gjs-caret-icon", "fa", "fa-caret-right");
    titleDiv.onclick = (event) => {
        let elem = titleDiv.firstChild;
        if (blockC.classList.contains("d-flex")) {
            blockC.classList.remove("d-flex");
            blockC.classList.add("d-none");
            elem.classList.remove("fa-caret-down");
            elem.classList.add("fa-caret-right");
        }
        else {
            blockC.classList.remove("d-none");
            blockC.classList.add("d-flex");
            elem.classList.remove("fa-caret-right");
            elem.classList.add("fa-caret-down");
            scaleSvgIcons(blockC);
        }
    };
    titleDiv.appendChild(icon);
    titleDiv.innerHTML += title;
    block.appendChild(titleDiv);
    block.appendChild(blockC);
    return block;
}
function createModuleDiv(moduleFactory, drawingArea) {
    let moduleDiv = document.createElement("div");
    moduleDiv.classList.add("gjs-block", "gjs-one-bg", "gjs-four-color-h");
    let labelDiv = document.createElement("div");
    labelDiv.classList.add("gjs-block-label");
    labelDiv.innerText = moduleFactory.displayName;
    let svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", "100px");
    svg.setAttribute("height", "70px");
    let item = new moduleFactory.ModuleRendererBuild().icon();
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.id = moduleFactory.id;
    g.classList.add("group-target");
    g.innerHTML = item.content;
    g.style.stroke = "currentColor";
    svg.appendChild(g);
    moduleDiv.appendChild(labelDiv);
    moduleDiv.append(svg);
    return moduleDiv;
}
function addDragingAbility(mdleFromId, direction, moduleDiv, moduleFactory, packId, drawingArea, appStore) {
    moduleDiv.draggable = true;
    moduleDiv.ondragstart = (ev) => {
        ev.dataTransfer.setData("text/plain", moduleFactory.id);
        ev.dataTransfer.dropEffect = "copy";
    };
    moduleDiv.ondragend = (ev) => {
        let mdleFrom = appStore.getModule(mdleFromId);
        let scale = drawingArea.overallTranform["scale"];
        let x0 = (ev.x - drawingArea.overallTranform.translateX) / scale;
        let y0 = (ev.y - 50 - drawingArea.overallTranform.translateY) / scale;
        let x = drawingArea.hScale.invert(x0);
        let y = drawingArea.vScale.invert(y0);
        let m1 = appStore.addModule(moduleFactory, [x, y]);
        if (direction == "down" && m1.inputSlots.length == 1 && mdleFrom.outputSlots.length == 1) {
            let c = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Connection(mdleFrom.outputSlots[0], m1.inputSlots[0]);
            appStore.addConnection(c);
        }
        if (direction == "up" && mdleFrom.inputSlots.length == 1 && m1.outputSlots.length == 1) {
            let c = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Connection(m1.outputSlots[0], mdleFrom.inputSlots[0]);
            appStore.addConnection(c);
        }
        appStore.selectModule(m1.moduleId);
    };
}
function createSuggestionsPanel(appStore, drawingArea, suggestions$) {
    suggestions$.subscribe(([mdleFrom, associations]) => {
        let modulesFactory = appStore.getModulesFactory();
        let container = document.getElementById("suggestions-panel");
        container.innerHTML = "";
        var fragment = document.createDocumentFragment();
        let connectionDown = createPart("down stream", []);
        let connectionUp = createPart("up stream", []);
        fragment.appendChild(connectionDown);
        fragment.appendChild(connectionUp);
        container.appendChild(fragment);
        let startDict = associations.starts.reduce((acc, start) => _.merge(acc, { [start.factoryId]: start }), {});
        Object.values(startDict).forEach((start) => {
            let moduleDiv = createModuleDiv(modulesFactory[start.factoryId], drawingArea);
            addDragingAbility(mdleFrom.moduleId, "up", moduleDiv, modulesFactory[start.factoryId], start.packId, drawingArea, appStore);
            connectionUp.children[1].appendChild(moduleDiv);
        });
        let endDict = associations.ends.reduce((acc, end) => _.merge(acc, { [end.factoryId]: end }), {});
        Object.values(endDict).forEach((end) => {
            let moduleDiv = createModuleDiv(modulesFactory[end.factoryId], drawingArea);
            addDragingAbility(mdleFrom.moduleId, "down", moduleDiv, modulesFactory[end.factoryId], end.packId, drawingArea, appStore);
            connectionDown.children[1].appendChild(moduleDiv);
        });
    });
    var container = document.createDocumentFragment();
    return container;
}
function scaleSvgIcons(dom) {
    dom.querySelectorAll(".group-target").forEach((g) => {
        if (g.style.transform)
            return;
        let parentBRect = g.parentElement.getBoundingClientRect();
        let bRect = g.getBoundingClientRect();
        let ty = parentBRect.top - bRect.top;
        let tx = parentBRect.left - bRect.left;
        let scale = Math.min(parentBRect.width / bRect.width, parentBRect.height / bRect.height);
        g.style.transform = `translate(${parentBRect.width / 4}px,${parentBRect.height / 4}px) scale(${0.5 * scale}) translate(${tx}px,${ty}px)`;
    });
}


/***/ }),

/***/ "./builder-editor/panels.ts":
/*!**********************************!*\
  !*** ./builder-editor/panels.ts ***!
  \**********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "getBuilderPanels": () => (/* binding */ getBuilderPanels)
/* harmony export */ });
function getBuilderPanels() {
    return [{
            id: 'app-builder-extensions',
            el: '#extensions-panel'
        }, {
            id: 'app-builder-modules',
            el: '#modules-panel',
            buttons: []
        }, {
            id: 'app-builder-components',
            el: '#components-panel',
            buttons: []
        }, {
            id: 'app-builder-attributes',
            el: '#attributes-panel',
            buttons: []
        },
        {
            id: 'builder-managers-actions',
            el: '#panel__builder-managers-actions',
            buttons: [
                {
                    id: 'show-attributes',
                    active: false,
                    label: '<i class="fas fa-tools"></i>',
                    command: 'show-attributes',
                },
                /*
                {
                    id: 'show-suggestions',
                    active: false,
                    label: '<i class="fas fa-lightbulb"></i>',
                    command: 'show-suggestions',
                },
                {
                    id: 'show-extensions',
                    active: false,
                    label: '<i class="fas fa-puzzle-piece"></i>',
                    command: 'show-extensions',
                }
            */
            ]
        },
        {
            id: 'builder-show-actions',
            el: '#panel__builder-show-actions',
            buttons: [
                {
                    id: 'show-hide-panels',
                    active: false,
                    label: '<i class="fas fa-eye"></i>',
                    command: 'show-hide-panels',
                }
            ]
        }];
}


/***/ }),

/***/ "./builder-editor/utils.view.ts":
/*!**************************************!*\
  !*** ./builder-editor/utils.view.ts ***!
  \**************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "grapesButton": () => (/* binding */ grapesButton)
/* harmony export */ });
function grapesButton({ onclick, title, classes }) {
    return {
        onclick,
        children: [
            {
                tag: 'span',
                class: 'gjs-pn-btn gjs-pn-active fv-text-focus d-flex align-items-center ',
                children: [
                    {
                        tag: 'i',
                        class: classes + " px-1"
                    },
                    { tag: 'div',
                        style: { 'font-weight': 'lighter', 'letter-spacing': '1px' },
                        class: 'px-1',
                        innerText: title
                    }
                ]
            }
        ]
    };
}


/***/ }),

/***/ "./builder-editor/views/adaptor-editor.view.ts":
/*!*****************************************************!*\
  !*** ./builder-editor/views/adaptor-editor.view.ts ***!
  \*****************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "AdaptorEditoView": () => (/* binding */ AdaptorEditoView)
/* harmony export */ });
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-view */ "@youwol/flux-view");
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var _code_editor_view__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./code-editor.view */ "./builder-editor/views/code-editor.view.ts");
/* harmony import */ var lodash__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! lodash */ "lodash");
/* harmony import */ var lodash__WEBPACK_IMPORTED_MODULE_4___default = /*#__PURE__*/__webpack_require__.n(lodash__WEBPACK_IMPORTED_MODULE_4__);
/* harmony import */ var _info_view__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./info.view */ "./builder-editor/views/info.view.ts");
/* harmony import */ var _data_tree_view__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! ./data-tree.view */ "./builder-editor/views/data-tree.view.ts");
/* harmony import */ var _input_status_view__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! ./input-status.view */ "./builder-editor/views/input-status.view.ts");
/* harmony import */ var _modal_view__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(/*! ./modal.view */ "./builder-editor/views/modal.view.ts");









var AdaptorEditoView;
(function (AdaptorEditoView) {
    class ExecutionError {
        constructor(message, row, col) {
            this.message = message;
            this.row = row;
            this.col = col;
        }
    }
    function parseError(stack) {
        try {
            let lines = stack.split('\n');
            let message = lines[0];
            lines = lines.filter(line => line.includes('eval') && line.split(',').length == 2);
            if (lines.length == 0) {
                return new ExecutionError(message, undefined, undefined);
            }
            let p = lines[0].split(',')[1].split('<anonymous>:')[1].split(')')[0];
            let [row, col] = [Number(p.split(':')[0]) - 2, Number(p.split(':')[1])];
            return new ExecutionError(message, row, col);
        }
        catch (e) {
            return new ExecutionError("Unidentified error", undefined, undefined);
        }
    }
    function invalidParsingView(error) {
        return {
            class: 'flex-grow-1 py-2',
            style: {
                'min-height': '0px',
                'font-family': 'monospace'
            },
            children: [
                {
                    innerText: 'error while executing the adaptor'
                },
                {
                    innerText: `${error.message}.` + (error.row ? ` Row:${error.row}, column:${error.col}` : '')
                }
            ]
        };
    }
    class State {
        constructor({ connection, initialCode, appStore }) {
            this.appStore = appStore;
            this.connection = connection;
            let codeContent$ = new rxjs__WEBPACK_IMPORTED_MODULE_1__.BehaviorSubject(initialCode);
            this.codeEditorState = new _code_editor_view__WEBPACK_IMPORTED_MODULE_3__.CodeEditorView.State({
                content$: codeContent$
            });
            this.mdleStart = this.appStore.getModule(connection.start.moduleId);
            this.mdleEnd = this.appStore.getModule(connection.end.moduleId);
            this.rawInput$ = this.mdleStart.getOutputSlot(connection.start.slotId).observable$;
            this.contract = this.mdleEnd.getInputSlot(this.connection.end.slotId).contract;
            this.adaptedInput$ = (0,rxjs__WEBPACK_IMPORTED_MODULE_1__.combineLatest)([
                codeContent$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.debounceTime)(0.5)),
                this.rawInput$
            ]).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.map)(([content, data]) => {
                try {
                    let result = new Function(content)()(data, this.mdleEnd.helpers);
                    result.configuration = lodash__WEBPACK_IMPORTED_MODULE_4__.merge({}, this.mdleEnd.getPersistentData(), result.configuration);
                    return result;
                }
                catch (e) {
                    return parseError(e.stack);
                }
            }));
        }
    }
    AdaptorEditoView.State = State;
    class View {
        constructor({ state, editorConfiguration, options, ...rest }) {
            Object.assign(this, rest);
            this.options = { ...View.defaultOptions, ...(options ? options : {}) };
            this.state = state;
            this.class = this.options.containerClass;
            this.style = this.options.containerStyle;
            this.children = [
                this.dataColumnView(),
                {
                    class: 'd-flex flex-grow-1 flex-column h-100 w-100 mx-2',
                    style: { 'min-width': '0px' },
                    children: [
                        new _code_editor_view__WEBPACK_IMPORTED_MODULE_3__.CodeEditorView.View({
                            state: state.codeEditorState,
                            editorConfiguration,
                            options: {
                                containerClass: 'w-100 h-50'
                            }
                        }),
                        this.statusView()
                    ]
                }
            ];
        }
        dataColumnView() {
            return {
                class: 'd-flex flex-column h-100 fv-text-primary w-50',
                style: { 'font-family': 'monospace' },
                children: [
                    this.rawInputView(),
                    this.adaptedInputView()
                ]
            };
        }
        statusView() {
            let info = "Presented here is a blind test of the input that is reaching the module's implementation " +
                "with respect to its internal validation rules. \n Make sure the trigger turn green before updating the adaptor.";
            return {
                style: { height: '33%', 'font-family': 'monospace' },
                class: 'overflow-auto flex-grow-1 d-flex flex-column',
                children: [
                    (0,_info_view__WEBPACK_IMPORTED_MODULE_5__.infoView)(info),
                    (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__.child$)(this.state.adaptedInput$, (input) => {
                        if (input instanceof ExecutionError || !input.data)
                            return invalidParsingView(input);
                        let state = new _input_status_view__WEBPACK_IMPORTED_MODULE_7__.InputStatusView.State({
                            mdle: this.state.mdleEnd,
                            adaptedInput: input,
                            contract: this.state.contract
                        });
                        return new _input_status_view__WEBPACK_IMPORTED_MODULE_7__.InputStatusView.View({
                            state,
                            options: {
                                containerClass: 'flex-grow-1 w-100 overflow-auto',
                                containerStyle: { 'min-height': '0px' }
                            }
                        });
                    })
                ]
            };
        }
        rawInputView() {
            let info = "Presented here is the latest input that have reached the adaptor, before any transformation. " +
                "The input that is actually reaching the module's implementation is presented below.";
            return {
                class: 'h-50 d-flex flex-column overflow-auto py-1',
                children: [
                    {
                        innerText: "Adaptor's input data",
                        class: 'text-center fv-text-focus'
                    },
                    {
                        class: 'flex-grow-1 d-flex flex-column', style: { 'min-height': '0' },
                        children: [
                            (0,_info_view__WEBPACK_IMPORTED_MODULE_5__.infoView)(info),
                            this.dataTreeView(this.state.rawInput$, 'input')
                        ]
                    }
                ]
            };
        }
        adaptedInputView() {
            let info = "Presented here is the input that is actually reaching the module's implementation. " +
                "Here, the configuration part of the input is merging the default one (defined in module's settings) " +
                "with the one returned by the adaptor (as presented in the previous tab).";
            return {
                class: 'h-50 d-flex flex-column overflow-auto py-1',
                children: [
                    {
                        innerText: "Module's input data",
                        class: 'text-center  fv-text-focus'
                    },
                    {
                        class: 'flex-grow-1 d-flex flex-column', style: { 'min-height': '0' },
                        children: [
                            (0,_info_view__WEBPACK_IMPORTED_MODULE_5__.infoView)(info),
                            this.dataTreeView(this.state.adaptedInput$, 'input')
                        ]
                    }
                ]
            };
        }
        dataTreeView(input$, rootNodeName) {
            let expandedNodes = [rootNodeName + "_0"];
            return {
                class: 'cm-s-blackboard overflow-auto flex-grow-1', style: { 'min-height': '0px' },
                children: [
                    (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__.child$)(input$, (result) => {
                        if (!result)
                            return { 'innerText': 'code not valid', class: 'p-3' };
                        let treeState = new _data_tree_view__WEBPACK_IMPORTED_MODULE_6__.DataTreeView.State({
                            title: rootNodeName,
                            data: result,
                            expandedNodes: expandedNodes
                        });
                        let treeView = new _data_tree_view__WEBPACK_IMPORTED_MODULE_6__.DataTreeView.View({
                            state: treeState,
                            connectedCallback: (elem) => {
                                elem.subscriptions.push(treeState.expandedNodes$.subscribe(nodes => expandedNodes = nodes));
                            }
                        });
                        return treeView;
                    }, { untilFirst: this.options.untilFirst })
                ]
            };
        }
    }
    View.defaultOptions = {
        containerClass: 'fv-bg-background p-3 fv-text-primary rounded d-flex h-100 w-100',
        containerStyle: {},
        untilFirst: {
            class: 'd-flex flex-column fv-text-primary ',
            style: { 'font-family': 'monospace' },
            children: [
                {
                    tag: 'p',
                    innerText: 'No data available: the module has not played any scenario yet. Having data available may help to write your code.'
                },
                {
                    tag: 'p',
                    innerText: 'Getting some data is usually as easy as connecting the input(s) of your module.'
                }
            ]
        }
    };
    AdaptorEditoView.View = View;
    function popupModal({ connection, initialCode, appStore, onUpdate }) {
        let state = new State({ connection, initialCode, appStore });
        let view = new View({
            state: state,
            options: {
                containerClass: 'p-3 d-flex flex-grow-1 w-100',
                containerStyle: { 'min-height': '0px' }
            }
        });
        _modal_view__WEBPACK_IMPORTED_MODULE_8__.ModalView.popup({
            view,
            style: { height: '50vh', width: '90vw', 'max-width': '1500px' }
        }).subscribe(() => {
            onUpdate(state.codeEditorState.content$.getValue());
        });
    }
    AdaptorEditoView.popupModal = popupModal;
})(AdaptorEditoView || (AdaptorEditoView = {}));


/***/ }),

/***/ "./builder-editor/views/assets-explorer.view.ts":
/*!******************************************************!*\
  !*** ./builder-editor/views/assets-explorer.view.ts ***!
  \******************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "AssetsExplorerView": () => (/* binding */ AssetsExplorerView)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @youwol/flux-view */ "@youwol/flux-view");
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! @youwol/fv-tree */ "@youwol/fv-tree");
/* harmony import */ var _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_tree__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_3__);
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_4___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_4__);
/* harmony import */ var _clients_assets_browser_client__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ../../clients/assets-browser.client */ "./clients/assets-browser.client.ts");






var AssetsExplorerView;
(function (AssetsExplorerView) {
    class State extends _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_2__.ImmutableTree.State {
        constructor({ appStore, selectionBuffer$ }) {
            super({
                rootNode: new RootNode({ favorites: State.favorites$.getValue() })
            });
            this.favorites = new Array();
            this.appStore = appStore;
            this.selectionBuffer$ = selectionBuffer$
                ? selectionBuffer$
                : (0,rxjs__WEBPACK_IMPORTED_MODULE_3__.of)([]);
            State.favorites$.subscribe(favorites => {
                localStorage.setItem('flux-builder#favorites', JSON.stringify(favorites));
            });
            this.selection$ = new rxjs__WEBPACK_IMPORTED_MODULE_3__.Subject();
            //this.clearBuffer()
        }
        toggleFavorite(node) {
            let favorites = getStoredFavorites();
            let originalId = node instanceof FavoriteNode ? node.favorite.id : node.id;
            if (favorites.find(f => f.id == originalId)) {
                favorites = favorites.filter(favorite => favorite.id != originalId);
                State.favorites$.next(favorites);
                this.removeNode(node instanceof FavoriteNode ? node.id : "favorite_" + originalId);
                return;
            }
            let favorite = new Favorite(originalId, node.name, node.type);
            favorites = favorites.concat([favorite]);
            State.favorites$.next(favorites);
            this.addChild('explorer', new FavoriteNode({ favorite }));
        }
    }
    State.favorites$ = new rxjs__WEBPACK_IMPORTED_MODULE_3__.BehaviorSubject(getStoredFavorites());
    AssetsExplorerView.State = State;
    class View extends _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_2__.ImmutableTree.View {
        constructor({ state, ...rest }) {
            super({
                state,
                headerView,
                ...rest
            });
        }
    }
    AssetsExplorerView.View = View;
    function headerView(state, node) {
        if (!(node instanceof ModuleItemNode)) {
            let favoriteClassBase = 'fas fa-star fa-xs fv-hover-opacity fv-pointer ';
            return {
                class: 'd-flex w-100 align-items-center fv-pointer',
                children: [
                    {
                        tag: 'i',
                        class: node.faIcon ? node.faIcon : ""
                    },
                    node instanceof FavoriteNode
                        ? {
                            tag: 'i', class: 'fas fa-star fa-xs px-1 fv-text-focus fv-hover-opacity',
                            onclick: (ev) => { ev.stopPropagation(); state.toggleFavorite(node); }
                        }
                        : {},
                    {
                        tag: 'span',
                        class: 'mx-2',
                        innerText: node.name,
                        style: { 'user-select': 'none' }
                    },
                    node instanceof AssetFolderNode
                        ? {
                            tag: 'i',
                            class: (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__.attr$)(State.favorites$, (favorites) => favorites.find(f => f.id == node.id)
                                ? favoriteClassBase + "fv-text-focus"
                                : favoriteClassBase + "fv-text-primary"),
                            onclick: (ev) => {
                                ev.stopPropagation();
                                state.toggleFavorite(node);
                            }
                        }
                        : {},
                    (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__.child$)(node.status$, (statusList) => statusList.find(status => status.type == 'request-pending')
                        ? { tag: 'i', class: 'fas fa-spinner fa-spin' }
                        : {})
                ]
            };
        }
        if (node instanceof ModuleItemNode) {
            return {
                class: 'd-flex w-100 align-items-baseline fv-pointer',
                onclick: () => state.selection$.next({ node: node, selected: true }),
                children: [
                    {
                        tag: 'i',
                        class: (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__.attr$)(state.selectionBuffer$, (buffer) => buffer.includes(node) ? 'fv-text-focus' : '', { wrapper: (d) => 'fas fa-cloud-download-alt fv-text-primary fv-hover-opacity ' + d })
                    },
                    {
                        tag: 'span',
                        class: 'mx-2 w-100',
                        innerText: node.name,
                        style: { 'user-select': 'none' }
                    }
                ]
            };
        }
    }
    class ExplorerTreeNode extends _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_2__.ImmutableTree.Node {
        constructor({ id, name, children, type, faIcon }) {
            super({ id, children });
            this.status$ = new rxjs__WEBPACK_IMPORTED_MODULE_3__.BehaviorSubject([]);
            this.name = name;
            this.faIcon = faIcon;
            this.type = type;
        }
        addStatus({ type, id }) {
            id = id || this.id;
            let newStatus = this.status$.getValue().concat({ type, id });
            this.status$.next(newStatus);
        }
        removeStatus({ type, id }) {
            id = id || this.id;
            let newStatus = this.status$.getValue().filter(s => s.type != type && s.id != id);
            this.status$.next(newStatus);
        }
        resolveChildren() {
            if (!this.children || Array.isArray(this.children))
                return;
            let uid = (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.uuidv4)();
            this.addStatus({ type: 'request-pending', id: uid });
            return super.resolveChildren().pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_4__.tap)(() => {
                this.removeStatus({ type: 'request-pending', id: uid });
            }));
        }
    }
    class FolderNode extends ExplorerTreeNode {
        constructor({ id, name, type, children, faIcon }) {
            super({
                id,
                name,
                type: type || "FolderNode",
                children,
                faIcon: faIcon ? faIcon : "fas fa-folder"
            });
        }
    }
    class RootNode extends FolderNode {
        constructor({ favorites, children }) {
            super({
                id: 'explorer',
                name: 'Explorer',
                type: "RootNode",
                children: children ? children : getRootChildren$()
            });
            this.favorites = favorites;
        }
    }
    class GroupNode extends FolderNode {
        constructor({ groupId, path, children }) {
            super({
                id: groupId, name: path.split('/').slice(-1)[0],
                type: "GroupNode",
                children: children ? children : getGroupChildren$(path),
                faIcon: "fas fa-users"
            });
            this.groupId = groupId;
            this.path = path;
        }
    }
    ;
    class DriveNode extends FolderNode {
        constructor({ driveId, name, children }) {
            super({
                id: driveId,
                name,
                type: "DriveNode",
                children: children ? children : getFolderChildren$(driveId),
                faIcon: "fas fa-hdd"
            });
            this.driveId = driveId;
        }
    }
    class AssetFolderNode extends FolderNode {
        constructor({ folderId, name, children }) {
            super({
                id: folderId,
                name,
                type: "AssetFolderNode",
                children: children ? children : getFolderChildren$(folderId)
            });
            this.folderId = folderId;
        }
    }
    class ItemNode extends ExplorerTreeNode {
        constructor({ id, name, type, children, faIcon }) {
            super({
                id,
                name,
                type: type || "ItemNode",
                children,
                faIcon
            });
        }
    }
    class AssetItemNode extends ItemNode {
        constructor({ assetId, name, rawId, children }) {
            super({
                id: assetId,
                name,
                type: "AssetItemNode",
                children: children ? children : getModules$(rawId), faIcon: "fas fa-box"
            });
            this.assetId = assetId;
        }
    }
    class ModuleItemNode extends ItemNode {
        constructor({ factory, library, fluxPacks }) {
            super({
                id: factory.uid,
                name: factory.displayName,
                type: "ModuleItemNode",
                faIcon: ""
            });
            this.factory = factory;
            this.library = library;
            this.fluxPacks = fluxPacks;
        }
    }
    AssetsExplorerView.ModuleItemNode = ModuleItemNode;
    class FavoriteNode extends ItemNode {
        constructor({ favorite }) {
            super({
                id: "favorite_" + favorite.id,
                name: favorite.name,
                type: "FavoriteNode",
                children: FavoriteNode.getChildrenFactory[favorite.type](favorite),
                faIcon: "fas fa-folder"
            });
            this.favorite = favorite;
        }
    }
    FavoriteNode.getChildrenFactory = {
        'AssetFolderNode': (favorite) => getFolderChildren$(favorite.id),
    };
    class Favorite {
        constructor(id, name, type) {
            this.id = id;
            this.name = name;
            this.type = type;
        }
    }
    function getStoredFavorites() {
        let favoritesStr = localStorage.getItem('flux-builder#favorites');
        let favorites = favoritesStr ? JSON.parse(favoritesStr) : [];
        return favorites;
    }
    function getRootChildren$() {
        let favorites = getStoredFavorites();
        return getGroupChildren$().pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_4__.map)(children => [...children, ...favorites.map(favorite => new FavoriteNode({ favorite }))]));
    }
    function getGroupChildren$(path = "") {
        return _clients_assets_browser_client__WEBPACK_IMPORTED_MODULE_5__.AssetsBrowserClient.getGroupChildren$(path).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_4__.map)((groupResp) => {
            return [
                ...groupResp.groups.map(group => {
                    return new GroupNode({ groupId: group.id, path: group.path });
                }),
                ...groupResp.drives.map(drive => {
                    return new DriveNode({ driveId: drive.driveId, name: drive.name });
                })
            ];
        }));
    }
    function getFolderChildren$(folderId) {
        return _clients_assets_browser_client__WEBPACK_IMPORTED_MODULE_5__.AssetsBrowserClient.getFolderChildren$(folderId).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_4__.map)((resp) => {
            return [
                ...resp.folders.map(folder => {
                    return new AssetFolderNode({ folderId: folder.folderId, name: folder.name });
                }),
                ...resp.items
                    .filter(item => item["kind"] == 'package')
                    .map(item => {
                    return new AssetItemNode({ assetId: item.assetId, name: item.name, rawId: item.rawId });
                })
            ];
        }));
    }
    function getModules$(assetId) {
        return _clients_assets_browser_client__WEBPACK_IMPORTED_MODULE_5__.AssetsBrowserClient.getModules$(assetId).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_4__.map)(({ factories, library, loadingGraph }) => {
            return factories.map(v => new ModuleItemNode({
                factory: v,
                library: { name: library.name, version: library.versions[0], namespace: library.namespace },
                fluxPacks: loadingGraph.lock.flat().filter(library => library.type == 'flux-pack')
            }));
        }));
    }
})(AssetsExplorerView || (AssetsExplorerView = {}));


/***/ }),

/***/ "./builder-editor/views/code-editor.view.ts":
/*!**************************************************!*\
  !*** ./builder-editor/views/code-editor.view.ts ***!
  \**************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "CodeEditorView": () => (/* binding */ CodeEditorView)
/* harmony export */ });
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-view */ "@youwol/flux-view");
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_2__);



var CodeEditorView;
(function (CodeEditorView) {
    class State {
        constructor({ content$ }) {
            this.content$ = content$;
        }
    }
    CodeEditorView.State = State;
    class View {
        constructor({ state, editorConfiguration, options, ...rest }) {
            Object.assign(this, rest);
            let styling = { ...View.defaultOptions, ...(options ? options : {}) };
            this.state = state;
            this.class = styling.containerClass;
            this.style = styling.containerStyle;
            let configuration = {
                ...{
                    value: state.content$.getValue(),
                    mode: 'javascript',
                    lineNumbers: true,
                    theme: 'blackboard',
                    extraKeys: {
                        "Tab": (cm) => cm.replaceSelection("    ", "end")
                    }
                },
                ...(editorConfiguration || {})
            };
            this.children = [
                (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__.child$)(fetchCodeMirror$(configuration.mode), () => {
                    return {
                        id: 'code-mirror-editor',
                        class: 'w-100 h-100',
                        connectedCallback: (elem) => {
                            let editor = window['CodeMirror'](elem, configuration);
                            editor.on("changes", () => {
                                state.content$.next(editor.getValue());
                            });
                        }
                    };
                })
            ];
        }
    }
    View.defaultOptions = {
        containerClass: 'h-100 w-100',
        containerStyle: {},
    };
    CodeEditorView.View = View;
    function fetchCodeMirror$(mode) {
        let cdn = window['@youwol/cdn-client'];
        let urlsMode = {
            "javascript": "codemirror#5.52.0~mode/javascript.min.js",
            "python": "codemirror#5.52.0~mode/python.min.js",
        };
        return (0,rxjs__WEBPACK_IMPORTED_MODULE_1__.from)(cdn.fetchBundles({ codemirror: { version: '5.52.0' } }, window)).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.mergeMap)(() => {
            let promise = cdn.fetchJavascriptAddOn([urlsMode[mode]], window);
            return (0,rxjs__WEBPACK_IMPORTED_MODULE_1__.from)(promise);
        }));
    }
})(CodeEditorView || (CodeEditorView = {}));


/***/ }),

/***/ "./builder-editor/views/code-property-editor.view.ts":
/*!***********************************************************!*\
  !*** ./builder-editor/views/code-property-editor.view.ts ***!
  \***********************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "CodePropertyEditorView": () => (/* binding */ CodePropertyEditorView)
/* harmony export */ });
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _code_editor_view__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./code-editor.view */ "./builder-editor/views/code-editor.view.ts");
/* harmony import */ var _modal_view__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./modal.view */ "./builder-editor/views/modal.view.ts");



var CodePropertyEditorView;
(function (CodePropertyEditorView) {
    class State {
        constructor({ mdle, initialCode }) {
            this.mdle = mdle;
            let content$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.BehaviorSubject(initialCode);
            this.codeEditorState = new _code_editor_view__WEBPACK_IMPORTED_MODULE_1__.CodeEditorView.State({ content$ });
        }
    }
    CodePropertyEditorView.State = State;
    class View {
        constructor({ state, editorConfiguration, options, ...rest }) {
            Object.assign(this, rest);
            this.options = { ...View.defaultOptions, ...(options ? options : {}) };
            this.state = state;
            this.class = this.options.containerClass;
            this.style = this.options.containerStyle;
            this.children = [
                this.moduleContextView(),
                {
                    class: 'd-flex flex-column h-100 w-100 mx-2',
                    children: [
                        new _code_editor_view__WEBPACK_IMPORTED_MODULE_1__.CodeEditorView.View({ state: this.state.codeEditorState, editorConfiguration })
                    ]
                }
            ];
        }
        moduleContextView() {
            return {};
        }
    }
    View.defaultOptions = {
        containerClass: 'fv-bg-background p-3 fv-text-primary rounded d-flex ',
        containerStyle: { height: '50vh', width: '90vw', 'max-width': '1500px' }
    };
    CodePropertyEditorView.View = View;
    function popupModal({ mdle, initialCode, editorConfiguration, onUpdate }) {
        let state = new State({ mdle, initialCode });
        let view = new View({
            state: state,
            editorConfiguration,
            options: {
                containerClass: 'p-2 d-flex flex-grow-1 w-100',
                containerStyle: { 'min-height': '0px' }
            }
        });
        _modal_view__WEBPACK_IMPORTED_MODULE_2__.ModalView.popup({
            view,
            style: { height: '50vh', width: '90vw', 'max-width': '1500px' }
        }).subscribe(() => {
            onUpdate(state.codeEditorState.content$.getValue());
        });
    }
    CodePropertyEditorView.popupModal = popupModal;
})(CodePropertyEditorView || (CodePropertyEditorView = {}));


/***/ }),

/***/ "./builder-editor/views/configuration-status.view.ts":
/*!***********************************************************!*\
  !*** ./builder-editor/views/configuration-status.view.ts ***!
  \***********************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "ConfigurationStatusView": () => (/* binding */ ConfigurationStatusView)
/* harmony export */ });
/* harmony import */ var _data_tree_view__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./data-tree.view */ "./builder-editor/views/data-tree.view.ts");

var ConfigurationStatusView;
(function (ConfigurationStatusView) {
    class State {
        constructor({ status, stringLengthLimit }) {
            this.status = status;
            this.stringLengthLimit = stringLengthLimit || 100;
            // Following hack is becaus of 'instanceof' issue with 2 versions of flux-core:
            // - one is used by flux-builder
            // - one is used by the application
            // They are not necessarly the same, not sure what's the best way to fix this problem yet
            let statusAny = status;
            if (statusAny.intrus.length == 0 && !statusAny.typeErrors && !statusAny.missings)
                return;
            if (statusAny.typeErrors && statusAny.typeErrors.length > 0)
                this.typingErrors = new _data_tree_view__WEBPACK_IMPORTED_MODULE_0__.DataTreeView.State({
                    title: 'typing errors',
                    data: statusAny.typeErrors
                });
            if (statusAny.missings && statusAny.missings.length > 0)
                this.missingFields = new _data_tree_view__WEBPACK_IMPORTED_MODULE_0__.DataTreeView.State({
                    title: 'missing fields',
                    data: statusAny.missings
                });
            if (statusAny.intrus.length > 0)
                this.unexpectedFields = new _data_tree_view__WEBPACK_IMPORTED_MODULE_0__.DataTreeView.State({
                    title: 'unexpected fields',
                    data: statusAny.intrus
                });
        }
    }
    ConfigurationStatusView.State = State;
    class View {
        constructor({ state, options, ...rest }) {
            Object.assign(this, rest);
            let styling = { ...View.defaultOptions, ...(options ? options : {}) };
            this.state = state;
            this.class = styling.containerClass;
            this.style = styling.containerStyle;
            let views = [this.state.typingErrors, this.state.missingFields, this.state.unexpectedFields]
                .filter(d => d)
                .map(state => new _data_tree_view__WEBPACK_IMPORTED_MODULE_0__.DataTreeView.View({ state }));
            this.children = (views.length == 0)
                ? [{ innerText: 'Your configuration is validated' }]
                : views;
        }
    }
    View.defaultOptions = {
        containerClass: 'd-flex flex-column',
        containerStyle: { 'min-height': '0px' },
    };
    ConfigurationStatusView.View = View;
    function journalWidget(data) {
        let dataState = new _data_tree_view__WEBPACK_IMPORTED_MODULE_0__.DataTreeView.State({
            title: "merged configuration",
            data: data.result
        });
        let configurationState = new ConfigurationStatusView.State({
            status: data
        });
        return {
            children: [
                {
                    class: 'd-flex justify-content-around w-100',
                    style: { 'white-space': 'nowrap' },
                    children: [
                        new _data_tree_view__WEBPACK_IMPORTED_MODULE_0__.DataTreeView.View({ state: dataState }),
                        { class: 'px-4' },
                        new ConfigurationStatusView.View({ state: configurationState })
                    ]
                }
            ]
        };
    }
    ConfigurationStatusView.journalWidget = journalWidget;
    /*
        function headerView(status: ConfigurationStatus<unknown>){
    
            let icon = {}
            if (status instanceof UnconsistentConfiguration)
                icon = { class:'fas fa-times fv-text-error px-1'}
            if (status instanceof ConsistentConfiguration &&  status.intrus.length>0)
                icon = { class:'fas fa-exclamation fv-text-danger px-1'}
            if (status instanceof ConsistentConfiguration &&  status.intrus.length==0)
                icon = { class:'fas fa-check fv-text-success px-1'}
            
            return {
                class:'d-flex align-items-center px-2',
                children:[
                    icon,
                    {innerText: 'configuration'}
                ]
            }
        }
        */
})(ConfigurationStatusView || (ConfigurationStatusView = {}));


/***/ }),

/***/ "./builder-editor/views/context.view.ts":
/*!**********************************************!*\
  !*** ./builder-editor/views/context.view.ts ***!
  \**********************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "ContextView": () => (/* binding */ ContextView)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @youwol/fv-tree */ "@youwol/fv-tree");
/* harmony import */ var _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_tree__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var _data_tree_view__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./data-tree.view */ "./builder-editor/views/data-tree.view.ts");
/* harmony import */ var _modal_view__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./modal.view */ "./builder-editor/views/modal.view.ts");




var ContextView;
(function (ContextView) {
    function nodeFactory(node) {
        if (node instanceof window['@youwol/flux-core'].Context) {
            return new ContextNode({ context: node });
        }
        if (node instanceof window['@youwol/flux-core'].ErrorLog) {
            return new LogNodeError({ log: node });
        }
        if (node instanceof window['@youwol/flux-core'].WarningLog) {
            return new LogNodeWarning({ log: node });
        }
        if (node instanceof window['@youwol/flux-core'].InfoLog) {
            return new LogNodeInfo({ log: node });
        }
    }
    class NodeBase extends _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_1__.ImmutableTree.Node {
        constructor({ id, children }) {
            super({ id, children });
        }
    }
    class ContextNode extends NodeBase {
        constructor({ context }) {
            super({ id: context.id, children: context.children.map(node => nodeFactory(node)) });
            this.context = context;
        }
    }
    class DataNodeBase extends NodeBase {
        constructor({ data }) {
            super({ id: (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.uuidv4)() });
            this.data = data;
        }
    }
    class LogNodeBase extends NodeBase {
        constructor({ log }) {
            super({ id: log.id, children: log.data != undefined ? [new DataNodeBase({ data: log.data })] : undefined });
            this.log = log;
        }
    }
    class LogNodeInfo extends LogNodeBase {
        constructor(d) { super(d); }
    }
    class LogNodeWarning extends LogNodeBase {
        constructor(d) { super(d); }
    }
    class LogNodeError extends LogNodeBase {
        constructor(d) { super(d); }
    }
    function nodePath(node) {
        return node.parent ? nodePath(node.parent).concat([node.id]) : [node.id];
    }
    class State extends _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_1__.ImmutableTree.State {
        constructor({ context, expandedNodes, selectedNode }) {
            super({
                rootNode: nodeFactory(context.root()),
                expandedNodes
            });
            this.rootCtx = context.root();
            this.context = context;
            this.tStart = this.rootCtx.startTimestamp;
            this.tEnd = this.rootCtx.startTimestamp + this.rootCtx.elapsed();
            selectedNode && this.selectedNode$.next(this.getNode(selectedNode));
        }
    }
    ContextView.State = State;
    class View {
        constructor({ state, options, ...rest }) {
            this.domId = 'contextView-view';
            Object.assign(this, rest);
            this.state = state;
            let styling = { ...View.defaultOptions, ...(options ? options : {}) };
            this.class = styling.containerClass;
            this.style = styling.containerStyle;
            let treeView = new _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_1__.ImmutableTree.View({
                state,
                headerView,
                class: styling.treeViewClass,
                style: styling.treeViewStyle,
                options: {
                    classes: {
                        header: "d-flex align-items-baseline fv-tree-header fv-hover-bg-background-alt "
                    }
                }
            });
            this.children = [
                treeView
            ];
        }
    }
    View.defaultOptions = {
        containerClass: 'p-4 fv-bg-background fv-text-primary',
        containerStyle: { width: "100%", height: "100%" },
        treeViewClass: 'h-100 overflow-auto',
        treeViewStyle: {}
    };
    ContextView.View = View;
    function reportContext(context, nodeId) {
        let state = new State({
            context,
            expandedNodes: nodeId ? nodePath(context).concat(nodeId) : nodePath(context),
            selectedNode: nodeId //errorLog.id
        });
        let view = new View({
            state,
        });
        _modal_view__WEBPACK_IMPORTED_MODULE_3__.ModalView.popup({
            view,
            style: { 'max-height': '75vh', width: '75vw' },
            options: { displayCancel: false, displayOk: false }
        });
    }
    ContextView.reportContext = reportContext;
    function headerView(state, node) {
        let heightBar = '3px';
        if (node instanceof ContextNode) {
            let tStart = node.context.startTimestamp - state.rootCtx.startTimestamp;
            let left = 100 * tStart / (state.tEnd - state.tStart);
            let width = 100 * node.context.elapsed() / (state.tEnd - state.tStart);
            let elapsed = Math.floor(100 * node.context.elapsed()) / 100;
            let classes = {
                [_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ContextStatus.FAILED]: "fas fa-times fv-text-error",
                [_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ContextStatus.SUCCESS]: "fas fa-check fv-text-success",
                [_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ContextStatus.RUNNING]: "fas fa-cog fa-spin",
            };
            return {
                class: 'w-100 pb-2',
                children: [
                    { class: "d-flex align-items-center",
                        children: [
                            {
                                tag: 'i',
                                class: classes[node.context.status()]
                            },
                            {
                                innerText: node.context.title + `  - ${elapsed} ms`,
                                class: 'fv-pointer px-2',
                                style: { 'font-family': 'fantasy' }
                            }
                        ]
                    },
                    { class: 'fv-bg-success',
                        style: {
                            top: '0px',
                            height: heightBar,
                            width: width + '%',
                            position: 'absolute',
                            left: left + '%'
                        }
                    }
                ]
            };
        }
        if (node instanceof LogNodeBase) {
            let tStart = node.log.timestamp - state.rootCtx.startTimestamp;
            let left = 100 * tStart / (state.tEnd - state.tStart);
            let classes = 'fv-text-primary fas fa-info';
            if (node instanceof LogNodeError) {
                classes = 'fv-text-error fas fa-times';
            }
            if (node instanceof LogNodeWarning) {
                classes = 'fv-text-focus fas fa-exclamation';
            }
            return {
                class: 'pb-1 fv-pointer w-100',
                children: [
                    {
                        class: 'd-flex align-items-center',
                        children: [
                            { class: classes },
                            { innerText: node.log.text, class: 'px-2' },
                        ]
                    },
                    { class: 'fv-bg-success rounded',
                        style: {
                            height: heightBar,
                            width: heightBar,
                            top: '0px',
                            position: 'absolute',
                            left: `calc( ${left}% - 5px)`
                        }
                    }
                ]
            };
        }
        if (node instanceof DataNodeBase) {
            let views = _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Journal.getViews(node.data).map(view => view.view);
            if (views.length > 0)
                return {
                    class: 'd-flex flex-grow-1',
                    style: { 'white-space': 'nowrap', "min-width": '0px' },
                    children: views
                };
            let dataState = new _data_tree_view__WEBPACK_IMPORTED_MODULE_2__.DataTreeView.State({
                title: "",
                data: node.data,
                expandedNodes: ['_0']
            });
            return {
                children: [
                    new _data_tree_view__WEBPACK_IMPORTED_MODULE_2__.DataTreeView.View({ state: dataState })
                ]
            };
        }
        return { innerText: "unknown type" };
    }
})(ContextView || (ContextView = {}));


/***/ }),

/***/ "./builder-editor/views/data-tree.view.ts":
/*!************************************************!*\
  !*** ./builder-editor/views/data-tree.view.ts ***!
  \************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "DataTreeView": () => (/* binding */ DataTreeView)
/* harmony export */ });
/* harmony import */ var _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/fv-tree */ "@youwol/fv-tree");
/* harmony import */ var _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_2__);



var DataTreeView;
(function (DataTreeView) {
    function nodeFactory(name, data, nestedIndex) {
        if (data == undefined)
            return new UndefinedNode({ name, nestedIndex });
        if (typeof data == 'string')
            return new StringNode({ name, data, nestedIndex });
        if (typeof data == 'number')
            return new NumberNode({ name, data, nestedIndex });
        if (typeof data == 'boolean')
            return new BoolNode({ name, data, nestedIndex });
        if (typeof data == 'function')
            return new FunctionNode({ name, data, nestedIndex });
        if (Array.isArray(data))
            return new ArrayNode({ name, data, nestedIndex });
        if (data instanceof ArrayBuffer)
            return new ArrayBufferNode({ name, data, nestedIndex });
        if (typeof data == 'object')
            return new ObjectNode({ name, data, nestedIndex });
        return new UnknownNode({ name, nestedIndex });
    }
    class DataNode extends _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0__.ImmutableTree.Node {
        constructor({ id, name, children, classes, nestedIndex }) {
            super({ id: id ? id : `${name}_${nestedIndex}`, children }); // `${Math.floor(Math.random()*1e6)}`
            this.name = name;
            this.classes = classes;
            this.nestedIndex = nestedIndex;
        }
    }
    DataTreeView.DataNode = DataNode;
    class UndefinedNode extends DataNode {
        constructor({ name, nestedIndex, id }) {
            super({ id, name, classes: "fv-text-disabled", nestedIndex });
        }
    }
    DataTreeView.UndefinedNode = UndefinedNode;
    class UnknownNode extends DataNode {
        constructor({ name, nestedIndex, id }) {
            super({ id, name, classes: "", nestedIndex });
        }
    }
    DataTreeView.UnknownNode = UnknownNode;
    class ValueNode extends DataNode {
        constructor({ name, data, classes, nestedIndex, id }) {
            super({ id, name, classes, nestedIndex });
            this.data = data;
        }
    }
    DataTreeView.ValueNode = ValueNode;
    class NumberNode extends ValueNode {
        constructor({ name, data, nestedIndex, id }) {
            super({ id, name, data, classes: "cm-number", nestedIndex });
        }
    }
    DataTreeView.NumberNode = NumberNode;
    class StringNode extends ValueNode {
        constructor({ name, data, nestedIndex, id }) {
            super({ id, name, data, classes: "cm-string", nestedIndex });
        }
    }
    DataTreeView.StringNode = StringNode;
    class BoolNode extends ValueNode {
        constructor({ name, data, nestedIndex, id }) {
            super({ id, name, data, classes: "cm-atom", nestedIndex });
        }
    }
    DataTreeView.BoolNode = BoolNode;
    class ArrayBufferNode extends ValueNode {
        constructor({ name, data, nestedIndex, id }) {
            super({ id, name, data, classes: "cm-string", nestedIndex });
        }
    }
    DataTreeView.ArrayBufferNode = ArrayBufferNode;
    class FunctionNode extends DataNode {
        constructor({ name, data, nestedIndex, id }) {
            super({ id, name, classes: "cm-def", nestedIndex });
            this.data = data;
        }
    }
    DataTreeView.FunctionNode = FunctionNode;
    class ObjectNode extends DataNode {
        constructor({ name, data, nestedIndex, id }) {
            super({
                id,
                name,
                children: (0,rxjs__WEBPACK_IMPORTED_MODULE_1__.of)(data).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.map)((data) => this.getChildrenNodes(data))),
                classes: "",
                nestedIndex
            });
            this.data = data;
        }
        getChildrenNodes(object) {
            let attributes = [];
            for (var key in object) {
                attributes.push(nodeFactory(key, object[key], this.nestedIndex + 1));
            }
            let functions = [];
            try {
                functions = Object.entries(object['__proto__']).map(([k, v]) => new FunctionNode({ name: k, data: v, nestedIndex: this.nestedIndex + 1 }));
            }
            catch (error) {
            }
            return [...attributes, ...functions];
        }
    }
    DataTreeView.ObjectNode = ObjectNode;
    class ArrayNode extends DataNode {
        constructor({ name, data, nestedIndex, id }) {
            super({
                id,
                name,
                children: (0,rxjs__WEBPACK_IMPORTED_MODULE_1__.of)(data).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.map)((data) => Object.entries(data).map(([k, v]) => nodeFactory(`${k}`, v, nestedIndex + 1)))),
                classes: "",
                nestedIndex
            });
            this.data = data;
        }
    }
    DataTreeView.ArrayNode = ArrayNode;
    class State extends _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0__.ImmutableTree.State {
        constructor({ title, data, expandedNodes, ...rest }) {
            super({
                rootNode: nodeFactory(title, data, 0),
                expandedNodes: expandedNodes,
                ...rest
            });
        }
    }
    DataTreeView.State = State;
    class View extends _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_0__.ImmutableTree.View {
        constructor({ state, options, ...rest }) {
            super({
                state,
                headerView: dataNodeHeaderView,
                class: View.getStyling(options).containerClass,
                style: View.getStyling(options).containerStyle,
                ...rest
            });
        }
        static getStyling(options) {
            return { ...View.defaultOptions, ...(options ? options : {}) };
        }
    }
    View.defaultOptions = {
        containerClass: 'cm-s-blackboard',
        containerStyle: { 'white-space': 'nowrap' },
    };
    DataTreeView.View = View;
    function dataNodeHeaderView(state, node) {
        if (node instanceof UnknownNode)
            return {
                class: 'd-flex fv-text-disabled flex-wrap',
                innerText: node.name
            };
        let content = "";
        if (node instanceof ValueNode) {
            content = String(node.data);
            if (typeof node.data == 'string')
                content = "'" + content + "'";
        }
        if (node instanceof UndefinedNode)
            content = 'undefined';
        if (node instanceof FunctionNode) {
            content = `f(${node.data.length} arg(s))`;
        }
        if (node instanceof ObjectNode)
            content = '{...}';
        if (node instanceof ArrayNode)
            content = '[...]';
        if (node instanceof ArrayBufferNode)
            content = `Array Buffer (${node.data.byteLength} bytes)`;
        return {
            class: 'd-flex fv-pointer',
            children: [
                {
                    innerText: node.name
                },
                {
                    class: 'px-2 w-100 ' + node.classes,
                    innerHTML: `<i>${content}</i>`,
                    style: {
                        "white-space": "nowrap",
                        overflow: "hidden",
                        "text-overflow": "ellipsis",
                        //"max-width": `${state.stringLengthLimit * 10}px`
                    }
                }
            ]
        };
    }
    DataTreeView.dataNodeHeaderView = dataNodeHeaderView;
})(DataTreeView || (DataTreeView = {}));


/***/ }),

/***/ "./builder-editor/views/expectation.view.ts":
/*!**************************************************!*\
  !*** ./builder-editor/views/expectation.view.ts ***!
  \**************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "ExpectationView": () => (/* binding */ ExpectationView)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @youwol/fv-tree */ "@youwol/fv-tree");
/* harmony import */ var _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_tree__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var _data_tree_view__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./data-tree.view */ "./builder-editor/views/data-tree.view.ts");



var ExpectationView;
(function (ExpectationView) {
    class ExpectationNode extends _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_1__.ImmutableTree.Node {
        constructor({ name, children, isRealized, evaluatedFrom }) {
            super({ id: (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.uuidv4)(), children });
            this.name = name;
            this.isRealized = isRealized;
            this.evaluatedFrom = evaluatedFrom;
        }
    }
    ExpectationView.ExpectationNode = ExpectationNode;
    class AnyOfNode extends ExpectationNode {
        constructor({ name, children, isRealized, evaluatedFrom }) {
            super({ name, children, isRealized, evaluatedFrom });
        }
    }
    ExpectationView.AnyOfNode = AnyOfNode;
    class AllOfNode extends ExpectationNode {
        constructor({ name, children, isRealized, evaluatedFrom }) {
            super({ name, children, isRealized, evaluatedFrom });
        }
    }
    ExpectationView.AllOfNode = AllOfNode;
    class OfNode extends ExpectationNode {
        constructor({ name, children, isRealized, evaluatedFrom }) {
            super({ name, children, isRealized, evaluatedFrom });
        }
    }
    ExpectationView.OfNode = OfNode;
    function parseReport(rootStatus) {
        let parseNode = (status) => {
            let nodeChildren = status.children && status.children.length > 0
                ? status.children.map(node => parseNode(node))
                : undefined;
            let dataNode = new _data_tree_view__WEBPACK_IMPORTED_MODULE_2__.DataTreeView.ObjectNode({
                id: (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.uuidv4)(),
                name: 'evaluated-with',
                data: status.fromValue,
                nestedIndex: 0
            });
            if (nodeChildren && status.succeeded != undefined && !(status.expectation instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Contract))
                nodeChildren = [dataNode, ...nodeChildren];
            if (status.expectation instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Contract)
                return new ExpectationNode({ name: status.expectation.description, children: nodeChildren,
                    isRealized: status.succeeded, evaluatedFrom: status.fromValue });
            if (status.expectation instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.AnyOf)
                return new AnyOfNode({ name: status.expectation.description, children: nodeChildren,
                    isRealized: status.succeeded, evaluatedFrom: status.fromValue });
            if (status.expectation instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.AllOf)
                return new AllOfNode({ name: status.expectation.description, children: nodeChildren,
                    isRealized: status.succeeded, evaluatedFrom: status.fromValue });
            if (status.expectation instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Of)
                return new OfNode({ name: status.expectation.description, children: nodeChildren,
                    isRealized: status.succeeded, evaluatedFrom: status.fromValue });
            if (status.expectation instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.OptionalsOf)
                return new AnyOfNode({ name: status.expectation.description, children: nodeChildren,
                    isRealized: status.succeeded, evaluatedFrom: status.fromValue });
            return new ExpectationNode({
                name: status.expectation.description,
                children: nodeChildren,
                isRealized: status.succeeded != undefined ? status.succeeded : undefined,
                evaluatedFrom: status.fromValue
            });
        };
        return parseNode(rootStatus);
    }
    ExpectationView.parseReport = parseReport;
    class ExecutionError {
        constructor(message, row, col) {
            this.message = message;
            this.row = row;
            this.col = col;
        }
    }
    ExpectationView.ExecutionError = ExecutionError;
    function parseError(stack) {
        try {
            let lines = stack.split('\n');
            let message = lines[0];
            lines = lines.filter(line => line.includes('eval') && line.split(',').length == 2);
            if (lines.length == 0) {
                return new ExecutionError(message, undefined, undefined);
            }
            let p = lines[0].split(',')[1].split('<anonymous>:')[1].split(')')[0];
            let [row, col] = [Number(p.split(':')[0]) - 2, Number(p.split(':')[1])];
            return new ExecutionError(message, row, col);
        }
        catch (e) {
            return new ExecutionError("Unidentified error", undefined, undefined);
        }
    }
    ExpectationView.parseError = parseError;
    class State {
        constructor({ status, expandedNodes$ }) {
            this.status = status;
            let treeNode = parseReport(this.status);
            let requiredRootNode = treeNode.children && treeNode.children.length > 0
                ? treeNode.children[0]
                : new ExpectationNode({ name: 'No required conditions defined', children: undefined, isRealized: true, evaluatedFrom: undefined });
            this.treeStateRequired = new _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_1__.ImmutableTree.State({
                rootNode: requiredRootNode,
                expandedNodes: expandedNodes$
            });
            let optionalRootNode = treeNode.children && treeNode.children.length > 1
                ? treeNode.children[1]
                : new ExpectationNode({ name: 'No optional conditions defined', children: undefined, isRealized: true, evaluatedFrom: undefined });
            this.treeStateOptionals = new _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_1__.ImmutableTree.State({
                rootNode: optionalRootNode,
                expandedNodes: expandedNodes$
            });
        }
    }
    ExpectationView.State = State;
    class View {
        constructor({ state, options, ...rest }) {
            Object.assign(this, rest);
            let styling = { ...View.defaultOptions, ...(options ? options : {}) };
            this.state = state;
            this.class = styling.containerClass;
            this.style = styling.containerStyle;
            this.children = [
                {
                    class: 'd-flex align-items-center',
                    children: [
                        {
                            class: this.state.status.succeeded ? 'fas fa-check fv-text-success' : 'fas fa-times fv-text-error',
                            style: { 'min-width': '25px' }
                        },
                        { class: 'px-2', innerText: this.state.status.expectation.description }
                    ]
                },
                {
                    class: 'pl-2 flex-grow-1 overflow-auto ', style: { 'min-height': '0px' },
                    children: [
                        {
                            class: 'pl-2',
                            children: [
                                new _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_1__.ImmutableTree.View({
                                    state: this.state.treeStateRequired,
                                    headerView
                                }),
                                new _youwol_fv_tree__WEBPACK_IMPORTED_MODULE_1__.ImmutableTree.View({
                                    state: this.state.treeStateOptionals,
                                    headerView
                                }),
                            ]
                        }
                    ]
                }
            ];
        }
    }
    View.defaultOptions = {
        containerClass: 'd-flex flex-column',
        containerStyle: { 'min-height': '0px' },
    };
    ExpectationView.View = View;
    function journalWidget(data) {
        let dataState = new _data_tree_view__WEBPACK_IMPORTED_MODULE_2__.DataTreeView.State({
            title: "incoming data",
            data: data.fromValue,
            expandedNodes: ["incoming data_0"]
        });
        let expectationState = new ExpectationView.State({
            status: data
        });
        return {
            children: [
                {
                    class: 'd-flex justify-content-around w-100',
                    style: { 'white-space': 'nowrap' },
                    children: [
                        new _data_tree_view__WEBPACK_IMPORTED_MODULE_2__.DataTreeView.View({ state: dataState }),
                        { class: 'px-4' },
                        new ExpectationView.View({ state: expectationState })
                    ]
                }
            ]
        };
    }
    ExpectationView.journalWidget = journalWidget;
    function headerView(_, node) {
        if (node instanceof _data_tree_view__WEBPACK_IMPORTED_MODULE_2__.DataTreeView.DataNode) {
            return _data_tree_view__WEBPACK_IMPORTED_MODULE_2__.DataTreeView.dataNodeHeaderView(undefined, node);
        }
        let classes = "";
        if (node.isRealized)
            classes = "fv-text-success";
        //if(node.isRealized==false)
        //    classes = "fv-text-error"
        if (node.isRealized == undefined)
            classes = "fv-text-disabled";
        let icon = "";
        if (node.isRealized)
            icon = "fas fa-check fv-text-success px-1";
        if (node.isRealized == false)
            icon = "fas fa-times fv-text-error px-1";
        if (node instanceof AllOfNode) {
            return {
                class: 'd-flex align-items-center',
                children: [
                    { class: classes + " " + icon },
                    { innerText: node.name, class: 'fv-text-primary px-2' },
                    { tag: 'i', class: 'fv-text-primary', innerText: "All of the following:" }
                ]
            };
        }
        if (node instanceof AnyOfNode) {
            return {
                class: 'd-flex align-items-center',
                children: [
                    { class: classes + " " + icon },
                    { innerText: node.name, class: 'fv-text-primary px-2' },
                    { tag: 'i', class: 'fv-text-primary', innerText: "Any of the following:" }
                ]
            };
        }
        if (node instanceof OfNode) {
            return {
                class: 'd-flex flex-align-items-center ',
                children: [
                    { class: icon },
                    { innerText: node.name, class: classes }
                ]
            };
        }
        return {
            class: 'd-flex flex-align-items-center ',
            children: [
                { class: icon },
                { innerText: node.name, class: classes }
            ]
        };
    }
})(ExpectationView || (ExpectationView = {}));


/***/ }),

/***/ "./builder-editor/views/import-modules.view.ts":
/*!*****************************************************!*\
  !*** ./builder-editor/views/import-modules.view.ts ***!
  \*****************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "ImportModulesView": () => (/* binding */ ImportModulesView)
/* harmony export */ });
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-view */ "@youwol/flux-view");
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _youwol_fv_button__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @youwol/fv-button */ "@youwol/fv-button");
/* harmony import */ var _youwol_fv_button__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_button__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_3__);
/* harmony import */ var _assets_explorer_view__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./assets-explorer.view */ "./builder-editor/views/assets-explorer.view.ts");
/* harmony import */ var _modal_view__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./modal.view */ "./builder-editor/views/modal.view.ts");






var ImportModulesView;
(function (ImportModulesView) {
    class State {
        constructor({ ok$ }) {
            this.buffer$ = new rxjs__WEBPACK_IMPORTED_MODULE_2__.BehaviorSubject([]);
            this.ok$ = ok$;
            this.explorerState = _assets_explorer_view__WEBPACK_IMPORTED_MODULE_4__.AssetsExplorerView.singletonState;
            this.explorerState.selectionBuffer$ = this.buffer$;
        }
    }
    class View {
        constructor({ state, options, ...rest }) {
            Object.assign(this, rest);
            this.options = { ...View.defaultOptions, ...(options ? options : {}) };
            this.state = state;
            this.class = this.options.containerClass;
            this.style = this.options.containerStyle;
            this.children = [
                this.bufferColumnView(),
                this.explorerView()
            ];
            this.connectedCallback = (elem) => {
                elem.subscriptions.push(this.state.explorerState.selection$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_3__.scan)((acc, { node, selected }) => [...acc.filter(e => e != node), ...(selected ? [node] : [])], [])).subscribe(d => this.state.buffer$.next(d)));
            };
        }
        bufferColumnView() {
            let okBttnView = new _youwol_fv_button__WEBPACK_IMPORTED_MODULE_1__.Button.View({
                state: new _youwol_fv_button__WEBPACK_IMPORTED_MODULE_1__.Button.State(this.state.ok$),
                contentView: () => ({ innerText: 'Import' }),
                class: "fv-btn fv-btn-primary fv-bg-focus"
            });
            return {
                class: 'px-2 d-flex flex-column w-25', style: { width: '200px' },
                children: [
                    {
                        class: 'w-100 text-center',
                        innerText: 'selection buffer',
                        style: { 'font-family': 'fantasy' }
                    },
                    (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__.child$)(this.state.buffer$, (nodes) => {
                        if (nodes.length > 0) {
                            return {
                                class: 'd-flex flex-column flex-grow-1 overflow-auto',
                                children: nodes.map(node => ({
                                    class: 'd-flex align-items-center',
                                    children: [
                                        { innerText: node.name },
                                        {
                                            class: 'fas fa-times px-2 yw-hover-opacity yw-pointer',
                                            onclick: () => {
                                                this.state.explorerState.selection$.next({ node, selected: false });
                                            }
                                        }
                                    ]
                                }))
                            };
                        }
                        return {
                            tag: 'div', class: 'py-2',
                            innerText: 'Pick one or more module(s) using the tabs on the right side to add them in your worksheet',
                            style: { 'font-style': 'italic', 'text-align': 'justify' }
                        };
                    }),
                    (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__.child$)(this.state.buffer$, (nodes) => nodes.length > 0 ? okBttnView : {})
                ]
            };
        }
        explorerView() {
            let view = new _assets_explorer_view__WEBPACK_IMPORTED_MODULE_4__.AssetsExplorerView.View({
                state: this.state.explorerState,
                class: 'h-100'
            });
            return {
                class: 'h-100 overflow-auto w-75 border rounded',
                children: [
                    view
                ]
            };
        }
    }
    View.defaultOptions = {
        containerClass: 'h-100 w-100 p-3 rounded d-flex solid rounded',
        containerStyle: {},
    };
    ImportModulesView.View = View;
    function popupModal(appStore, onImport) {
        let import$ = new rxjs__WEBPACK_IMPORTED_MODULE_2__.Subject();
        let state = new State({
            ok$: import$
        });
        let view = new View({ state: state });
        _modal_view__WEBPACK_IMPORTED_MODULE_5__.ModalView.popup({
            view,
            ok$: import$,
            options: { displayOk: false, displayCancel: false }
        }).subscribe(() => {
            onImport(state.buffer$.getValue());
        });
    }
    ImportModulesView.popupModal = popupModal;
})(ImportModulesView || (ImportModulesView = {}));


/***/ }),

/***/ "./builder-editor/views/index.ts":
/*!***************************************!*\
  !*** ./builder-editor/views/index.ts ***!
  \***************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "AdaptorEditoView": () => (/* reexport safe */ _adaptor_editor_view__WEBPACK_IMPORTED_MODULE_0__.AdaptorEditoView),
/* harmony export */   "AssetsExplorerView": () => (/* reexport safe */ _assets_explorer_view__WEBPACK_IMPORTED_MODULE_1__.AssetsExplorerView),
/* harmony export */   "CodeEditorView": () => (/* reexport safe */ _code_editor_view__WEBPACK_IMPORTED_MODULE_2__.CodeEditorView),
/* harmony export */   "CodePropertyEditorView": () => (/* reexport safe */ _code_property_editor_view__WEBPACK_IMPORTED_MODULE_3__.CodePropertyEditorView),
/* harmony export */   "ConfigurationStatusView": () => (/* reexport safe */ _configuration_status_view__WEBPACK_IMPORTED_MODULE_4__.ConfigurationStatusView),
/* harmony export */   "ContextView": () => (/* reexport safe */ _context_view__WEBPACK_IMPORTED_MODULE_5__.ContextView),
/* harmony export */   "DataTreeView": () => (/* reexport safe */ _data_tree_view__WEBPACK_IMPORTED_MODULE_6__.DataTreeView),
/* harmony export */   "ExpectationView": () => (/* reexport safe */ _expectation_view__WEBPACK_IMPORTED_MODULE_7__.ExpectationView),
/* harmony export */   "ImportModulesView": () => (/* reexport safe */ _import_modules_view__WEBPACK_IMPORTED_MODULE_8__.ImportModulesView),
/* harmony export */   "infoView": () => (/* reexport safe */ _info_view__WEBPACK_IMPORTED_MODULE_9__.infoView),
/* harmony export */   "InputStatusView": () => (/* reexport safe */ _input_status_view__WEBPACK_IMPORTED_MODULE_10__.InputStatusView),
/* harmony export */   "ShareUriView": () => (/* reexport safe */ _share_uri_view__WEBPACK_IMPORTED_MODULE_11__.ShareUriView)
/* harmony export */ });
/* harmony import */ var _adaptor_editor_view__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./adaptor-editor.view */ "./builder-editor/views/adaptor-editor.view.ts");
/* harmony import */ var _assets_explorer_view__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./assets-explorer.view */ "./builder-editor/views/assets-explorer.view.ts");
/* harmony import */ var _code_editor_view__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./code-editor.view */ "./builder-editor/views/code-editor.view.ts");
/* harmony import */ var _code_property_editor_view__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./code-property-editor.view */ "./builder-editor/views/code-property-editor.view.ts");
/* harmony import */ var _configuration_status_view__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./configuration-status.view */ "./builder-editor/views/configuration-status.view.ts");
/* harmony import */ var _context_view__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./context.view */ "./builder-editor/views/context.view.ts");
/* harmony import */ var _data_tree_view__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! ./data-tree.view */ "./builder-editor/views/data-tree.view.ts");
/* harmony import */ var _expectation_view__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! ./expectation.view */ "./builder-editor/views/expectation.view.ts");
/* harmony import */ var _import_modules_view__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(/*! ./import-modules.view */ "./builder-editor/views/import-modules.view.ts");
/* harmony import */ var _info_view__WEBPACK_IMPORTED_MODULE_9__ = __webpack_require__(/*! ./info.view */ "./builder-editor/views/info.view.ts");
/* harmony import */ var _input_status_view__WEBPACK_IMPORTED_MODULE_10__ = __webpack_require__(/*! ./input-status.view */ "./builder-editor/views/input-status.view.ts");
/* harmony import */ var _share_uri_view__WEBPACK_IMPORTED_MODULE_11__ = __webpack_require__(/*! ./share-uri.view */ "./builder-editor/views/share-uri.view.ts");














/***/ }),

/***/ "./builder-editor/views/info.view.ts":
/*!*******************************************!*\
  !*** ./builder-editor/views/info.view.ts ***!
  \*******************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "infoView": () => (/* binding */ infoView)
/* harmony export */ });
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-view */ "@youwol/flux-view");
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_1__);


function infoView(text) {
    let infoToggled$ = new rxjs__WEBPACK_IMPORTED_MODULE_1__.BehaviorSubject(false);
    return (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__.child$)(infoToggled$, (toggled) => {
        return {
            class: 'p-1 d-flex',
            children: [
                { tag: 'i',
                    class: 'fas fa-info fv-hover-bg-background-alt p-1 fv-pointer rounded '
                        + (toggled ? 'fv-bg-background-alt' : ''),
                    onclick: () => infoToggled$.next(!infoToggled$.getValue())
                },
                toggled
                    ? { class: 'p-1 px-2 fv-bg-background-alt rounded', style: { 'text-align': 'justify', 'font-style': 'italic' },
                        innerText: text
                    }
                    : {}
            ]
        };
    });
}


/***/ }),

/***/ "./builder-editor/views/input-status.view.ts":
/*!***************************************************!*\
  !*** ./builder-editor/views/input-status.view.ts ***!
  \***************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "InputStatusView": () => (/* binding */ InputStatusView)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _youwol_fv_tabs__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @youwol/fv-tabs */ "@youwol/fv-tabs");
/* harmony import */ var _youwol_fv_tabs__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_tabs__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var _configuration_status_view__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./configuration-status.view */ "./builder-editor/views/configuration-status.view.ts");
/* harmony import */ var _expectation_view__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./expectation.view */ "./builder-editor/views/expectation.view.ts");





var InputStatusView;
(function (InputStatusView) {
    class DataTab extends _youwol_fv_tabs__WEBPACK_IMPORTED_MODULE_1__.Tabs.TabData {
        constructor() { super('data', 'data'); }
    }
    class ConfigTab extends _youwol_fv_tabs__WEBPACK_IMPORTED_MODULE_1__.Tabs.TabData {
        constructor() { super('configuration', 'configuration'); }
    }
    class State {
        constructor({ mdle, adaptedInput, contract, selectedTabId$ }) {
            this.selectedTabId$ = selectedTabId$ || new rxjs__WEBPACK_IMPORTED_MODULE_2__.BehaviorSubject("data");
            this.tabState = new _youwol_fv_tabs__WEBPACK_IMPORTED_MODULE_1__.Tabs.State([new DataTab(), new ConfigTab()], selectedTabId$);
            this.configStatus = (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.mergeConfiguration)(mdle.configuration.data, adaptedInput.configuration);
            let context = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Context("", {});
            this.dataStatus = contract.resolve(adaptedInput.data, context);
        }
    }
    InputStatusView.State = State;
    class View {
        constructor({ state, options, ...rest }) {
            Object.assign(this, rest);
            this.options = { ...View.defaultOptions, ...(options ? options : {}) };
            this.state = state;
            this.class = this.options.containerClass;
            this.style = this.options.containerStyle;
            let expandedNodesExpectation$ = new rxjs__WEBPACK_IMPORTED_MODULE_2__.BehaviorSubject(['optional', 'required']);
            let tabView = new _youwol_fv_tabs__WEBPACK_IMPORTED_MODULE_1__.Tabs.View({
                state: this.state.tabState,
                contentView: (state, data) => {
                    if (data instanceof DataTab) {
                        let state = new _expectation_view__WEBPACK_IMPORTED_MODULE_4__.ExpectationView.State({
                            status: this.state.dataStatus,
                            expandedNodes$: expandedNodesExpectation$
                        });
                        return new _expectation_view__WEBPACK_IMPORTED_MODULE_4__.ExpectationView.View({ state });
                    }
                    if (data instanceof ConfigTab) {
                        let state = new _configuration_status_view__WEBPACK_IMPORTED_MODULE_3__.ConfigurationStatusView.State({
                            status: this.state.configStatus
                        });
                        return new _configuration_status_view__WEBPACK_IMPORTED_MODULE_3__.ConfigurationStatusView.View({ state });
                    }
                },
                headerView: (state, data) => {
                    if (data instanceof DataTab)
                        return dataHeaderView(this.state.dataStatus);
                    if (data instanceof ConfigTab)
                        return configurationHeaderView(this.state.configStatus);
                    return { innerText: data.name, class: "px-2" };
                },
                class: 'h-100 d-flex flex-column', style: { 'min-height': '0px' },
                options: {
                    containerStyle: { 'min-height': '0px' },
                    containerClass: 'p-2 border flex-grow-1 overflow-auto'
                }
            });
            this.children = [tabView];
        }
    }
    View.defaultOptions = {
        containerClass: 'h-100 w-100',
        containerStyle: {}
    };
    InputStatusView.View = View;
    function dataHeaderView(status) {
        let classes = 'fas fa-check fv-text-success px-1';
        if (!status)
            classes = 'fas fa-question px-1';
        else if (!status.succeeded)
            classes = 'fas fa-times fv-text-error px-1';
        return {
            class: 'd-flex align-items-center px-2',
            children: [
                { class: classes },
                { innerText: 'data' }
            ]
        };
    }
    function configurationHeaderView(status) {
        let icon = {};
        if (status instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.InconsistentConfiguration)
            icon = { class: 'fas fa-times fv-text-error px-1' };
        if (status instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ConsistentConfiguration && status.intrus.length > 0)
            icon = { class: 'fas fa-exclamation fv-text-danger px-1' };
        if (status instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ConsistentConfiguration && status.intrus.length == 0)
            icon = { class: 'fas fa-check fv-text-success px-1' };
        return {
            class: 'd-flex align-items-center px-2',
            children: [
                icon,
                { innerText: 'configuration' }
            ]
        };
    }
})(InputStatusView || (InputStatusView = {}));


/***/ }),

/***/ "./builder-editor/views/journals.view.ts":
/*!***********************************************!*\
  !*** ./builder-editor/views/journals.view.ts ***!
  \***********************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "JournalsView": () => (/* binding */ JournalsView)
/* harmony export */ });
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-view */ "@youwol/flux-view");
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _youwol_fv_input__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @youwol/fv-input */ "@youwol/fv-input");
/* harmony import */ var _youwol_fv_input__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_input__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_3__);
/* harmony import */ var _context_view__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./context.view */ "./builder-editor/views/context.view.ts");
/* harmony import */ var _modal_view__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./modal.view */ "./builder-editor/views/modal.view.ts");






var JournalsView;
(function (JournalsView) {
    class State {
        constructor({ module }) {
            this.module = module;
        }
    }
    JournalsView.State = State;
    class View {
        constructor({ state, ...rest }) {
            Object.assign(this, rest);
            this.state = state;
            this.class = this.class || View.defaultOptions.containerClass;
            this.style = this.style || View.defaultOptions.containerStyle;
            if (this.state.module.journals.length == 0) {
                this.children = [
                    this.noJournalsAvailableView()
                ];
                return;
            }
            if (this.state.module.journals.length == 1) {
                this.children = [
                    this.journalView(this.state.module.journals[0])
                ];
                return;
            }
            let journalSelected$ = new rxjs__WEBPACK_IMPORTED_MODULE_2__.BehaviorSubject(this.state.module.journals[0].title);
            this.children = [
                this.selectJournalView(journalSelected$),
                (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__.child$)(journalSelected$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_3__.map)(title => this.state.module.journals.find(journal => journal.title == title))), (journal) => this.journalView(journal))
            ];
        }
        noJournalsAvailableView() {
            return {
                innerText: 'The module does not contains journals yet, it is likely that it did not run already.'
            };
        }
        selectJournalView(journalSelected$) {
            let items = this.state.module.journals.map((journal) => {
                return new _youwol_fv_input__WEBPACK_IMPORTED_MODULE_1__.Select.ItemData(journal.title, journal.title);
            });
            let state = new _youwol_fv_input__WEBPACK_IMPORTED_MODULE_1__.Select.State(items, journalSelected$);
            return {
                class: 'd-flex align-items-center py-2',
                children: [
                    { innerText: 'Available reports:', class: 'px-2' },
                    new _youwol_fv_input__WEBPACK_IMPORTED_MODULE_1__.Select.View({ state })
                ]
            };
        }
        journalView(journal) {
            let state = new _context_view__WEBPACK_IMPORTED_MODULE_4__.ContextView.State({ context: journal.entryPoint,
                expandedNodes: [journal.entryPoint.id]
            });
            return {
                class: "h-100 d-flex flex-column",
                children: [
                    { class: 'd-flex align-items-center justify-content-center',
                        children: [
                            {
                                tag: 'i',
                                class: 'fas fa-newspaper fa-2x px-3'
                            },
                            {
                                class: 'text-center py-2',
                                style: { 'font-family': 'fantasy', 'font-size': 'larger' },
                                innerText: journal.title
                            }
                        ]
                    },
                    new _context_view__WEBPACK_IMPORTED_MODULE_4__.ContextView.View({
                        state,
                        options: {
                            containerClass: 'p-4 flex-grow-1 overflow-auto'
                        }
                    })
                ]
            };
        }
    }
    View.defaultOptions = {
        containerClass: 'd-flex flex-column p-3',
        containerStyle: { 'min-height': '0px' },
    };
    JournalsView.View = View;
    function popupModal({ module }) {
        let state = new State({ module });
        let view = new View({ state });
        _modal_view__WEBPACK_IMPORTED_MODULE_5__.ModalView.popup({
            view,
            style: { 'max-height': '75vh', width: '75vw' },
            options: { displayCancel: false, displayOk: false }
        }).subscribe(() => {
        });
    }
    JournalsView.popupModal = popupModal;
})(JournalsView || (JournalsView = {}));


/***/ }),

/***/ "./builder-editor/views/modal.view.ts":
/*!********************************************!*\
  !*** ./builder-editor/views/modal.view.ts ***!
  \********************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "ModalView": () => (/* binding */ ModalView)
/* harmony export */ });
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-view */ "@youwol/flux-view");
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _youwol_fv_button__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @youwol/fv-button */ "@youwol/fv-button");
/* harmony import */ var _youwol_fv_button__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_button__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var _youwol_fv_group__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! @youwol/fv-group */ "@youwol/fv-group");
/* harmony import */ var _youwol_fv_group__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_group__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_3__);




var ModalView;
(function (ModalView) {
    function popup({ view, style, ok$, options }) {
        options = options || { displayOk: true, displayCancel: true };
        let okBttn = new _youwol_fv_button__WEBPACK_IMPORTED_MODULE_1__.Button.View({
            state: new _youwol_fv_button__WEBPACK_IMPORTED_MODULE_1__.Button.State(),
            contentView: () => ({ innerText: 'Ok' }),
            class: "fv-btn fv-btn-primary fv-bg-focus mr-2"
        });
        let cancelBttn = _youwol_fv_button__WEBPACK_IMPORTED_MODULE_1__.Button.simpleTextButton('Cancel');
        let modalState = new _youwol_fv_group__WEBPACK_IMPORTED_MODULE_2__.Modal.State(ok$);
        let modalDiv = (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__.render)(new _youwol_fv_group__WEBPACK_IMPORTED_MODULE_2__.Modal.View({
            state: modalState,
            contentView: () => {
                return {
                    class: 'border rounded fv-text-primary fv-bg-background d-flex flex-column',
                    style: style ? style : { height: '50vh', width: '50vw', 'max-width': '1500px' },
                    children: [
                        view,
                        {
                            class: 'd-flex p-2',
                            children: [
                                options.displayOk ? okBttn : undefined,
                                options.displayCancel ? cancelBttn : undefined
                            ].filter(d => d)
                        }
                    ]
                };
            },
            connectedCallback: (elem) => {
                let subs = [
                    okBttn.state.click$.subscribe(() => modalState.ok$.next()),
                    cancelBttn.state.click$.subscribe(() => modalState.cancel$.next()),
                    (0,rxjs__WEBPACK_IMPORTED_MODULE_3__.merge)(modalState.cancel$, modalState.ok$).subscribe(() => modalDiv.remove())
                ];
                elem.subscriptions = [...elem.subscriptions, ...subs];
            }
        }));
        document.querySelector("body").appendChild(modalDiv);
        return modalState.ok$;
    }
    ModalView.popup = popup;
})(ModalView || (ModalView = {}));


/***/ }),

/***/ "./builder-editor/views/share-uri.view.ts":
/*!************************************************!*\
  !*** ./builder-editor/views/share-uri.view.ts ***!
  \************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "ShareUriView": () => (/* binding */ ShareUriView)
/* harmony export */ });
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-view */ "@youwol/flux-view");
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _youwol_fv_button__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @youwol/fv-button */ "@youwol/fv-button");
/* harmony import */ var _youwol_fv_button__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_button__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var _youwol_fv_input__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! @youwol/fv-input */ "@youwol/fv-input");
/* harmony import */ var _youwol_fv_input__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_input__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_3__);
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_4___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_4__);
/* harmony import */ var _modal_view__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./modal.view */ "./builder-editor/views/modal.view.ts");






var ShareUriView;
(function (ShareUriView) {
    class State {
        constructor({ appStore }) {
            let selectItems = [
                new _youwol_fv_input__WEBPACK_IMPORTED_MODULE_2__.Select.ItemData('youwol-url', 'YouWol Platform URL'),
                new _youwol_fv_input__WEBPACK_IMPORTED_MODULE_2__.Select.ItemData('relative-url', 'Relative URL')
            ];
            if (location.hostname == 'localhost')
                selectItems.push(new _youwol_fv_input__WEBPACK_IMPORTED_MODULE_2__.Select.ItemData('localhost-url', 'Localhost URL'));
            this.selectState = new _youwol_fv_input__WEBPACK_IMPORTED_MODULE_2__.Select.State(selectItems, 'youwol-url');
            this.sourceURI$ = (0,rxjs__WEBPACK_IMPORTED_MODULE_3__.combineLatest)([appStore.projectURI$(), this.selectState.selectionId$]);
        }
        toUrl(uri, mode) {
            if (mode == 'relative-url')
                return `${uri}`;
            if (mode == 'localhost-url')
                return `${location.hostname}:${location.port}${uri}`;
            return `https://platform.youwol.com${uri}`;
        }
    }
    ShareUriView.State = State;
    class View {
        constructor({ state, ...rest }) {
            Object.assign(this, rest);
            this.state = state;
            this.class = this.class || View.defaultOptions.containerClass;
            this.style = this.style || View.defaultOptions.containerStyle;
            let copyLinkBttn = new _youwol_fv_button__WEBPACK_IMPORTED_MODULE_1__.Button.View({
                state: new _youwol_fv_button__WEBPACK_IMPORTED_MODULE_1__.Button.State(),
                contentView: () => ({ innerText: '' }),
                class: "fv-btn fv-btn-primary fv-bg-focus fas fa-copy ml-2"
            });
            this.connectedCallback = (elem) => {
                elem.subscriptions.push(copyLinkBttn.state.click$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_4__.mergeMap)(() => state.sourceURI$), (0,rxjs_operators__WEBPACK_IMPORTED_MODULE_4__.mergeMap)(([uri, mode]) => (0,rxjs__WEBPACK_IMPORTED_MODULE_3__.from)(navigator.clipboard.writeText(state.toUrl(uri, mode))))).subscribe(() => {
                    console.log("Copied:::!!!");
                    //onUpdate( state.codeEditorState.content$.getValue())
                }));
            };
            this.children = [
                {
                    innerText: 'The following url can be used to share your application:'
                },
                new _youwol_fv_input__WEBPACK_IMPORTED_MODULE_2__.Select.View({ state: state.selectState }),
                {
                    class: 'd-flex align-items-center',
                    children: [
                        {
                            style: { 'text-overflow': 'ellipsis', 'white-space': 'nowrap', 'overflow': 'hidden', 'font-family': 'monospace' },
                            innerText: (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_0__.attr$)(state.sourceURI$, ([uri, mode]) => state.toUrl(uri, mode))
                        },
                        copyLinkBttn
                    ]
                },
                {
                    class: 'd-flex align-items-center fv-bg-background-alt rounded my-3',
                    children: [
                        {
                            class: 'fas fa-exclamation fv-text-focus px-2'
                        },
                        {
                            innerText: "This feature is a work in progress, it is expected to work with 'relatively' small application for now. " +
                                "Also, the consumer of this link will need to have access to all packages/modules/resources included in your app."
                        }
                    ]
                }
            ];
        }
    }
    View.defaultOptions = {
        containerClass: 'd-flex flex-column p-3',
        containerStyle: { 'min-height': '0px' },
    };
    ShareUriView.View = View;
    function popupModal(appStore) {
        let state = new State({ appStore });
        let view = new View({ state });
        _modal_view__WEBPACK_IMPORTED_MODULE_5__.ModalView.popup({
            view,
            style: { width: '75vw', 'max-width': '1000px' },
            options: { displayOk: false, displayCancel: false }
        });
    }
    ShareUriView.popupModal = popupModal;
})(ShareUriView || (ShareUriView = {}));


/***/ }),

/***/ "./clients/assets-browser.client.ts":
/*!******************************************!*\
  !*** ./clients/assets-browser.client.ts ***!
  \******************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "AssetsBrowserClient": () => (/* binding */ AssetsBrowserClient)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var _youwol_cdn_client__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! @youwol/cdn-client */ "@youwol/cdn-client");
/* harmony import */ var _youwol_cdn_client__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(_youwol_cdn_client__WEBPACK_IMPORTED_MODULE_3__);




class AssetsBrowserClient {
    static setHeaders(headers) {
        AssetsBrowserClient.headers = headers;
    }
    static getAsset$(assetId) {
        let url = AssetsBrowserClient.urlBaseAssets + `/${assetId}`;
        let request = new Request(url, { headers: AssetsBrowserClient.headers });
        return (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.createObservableFromFetch)(request);
    }
    static getFolderChildren$(folderId) {
        let url = `/api/assets-gateway/tree/folders/${folderId}/children`;
        let request = new Request(url, { headers: AssetsBrowserClient.headers });
        return (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.createObservableFromFetch)(request);
    }
    static getGroupChildrenDrives$(groupId) {
        let url = `/api/assets-gateway/tree/groups/${groupId}/drives`;
        let request = new Request(url, { headers: AssetsBrowserClient.headers });
        return (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.createObservableFromFetch)(request);
    }
    static getGroupChildren$(pathParent = "") {
        let url = '/api/assets-gateway/groups';
        let request = new Request(url, { headers: AssetsBrowserClient.headers });
        let start$ = this.allGroups
            ? (0,rxjs__WEBPACK_IMPORTED_MODULE_1__.of)(this.allGroups)
            : (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.createObservableFromFetch)(request).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.tap)(({ groups }) => this.allGroups = groups), (0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.map)(({ groups }) => groups));
        return start$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.mergeMap)((allGroups) => {
            let selectedGroups = allGroups
                .filter(grp => {
                if (pathParent == "")
                    return grp.path == "private" || grp.path == "/youwol-users";
                return grp.path != pathParent && grp.path.includes(pathParent) && (grp.path.slice(pathParent.length).match(/\//g)).length == 1;
            });
            if (pathParent == "")
                return (0,rxjs__WEBPACK_IMPORTED_MODULE_1__.of)({ groups: selectedGroups, drives: [], groupId: undefined });
            let groupId = allGroups.find(g => g.path == pathParent).id;
            return AssetsBrowserClient
                .getGroupChildrenDrives$(groupId)
                .pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.map)(({ drives }) => {
                return { groupId, groups: selectedGroups, drives };
            }));
        }));
    }
    static getModules$(rawId) {
        let url = `/api/assets-gateway/raw/package/metadata/${rawId}`;
        let request = new Request(url, { headers: AssetsBrowserClient.headers });
        return (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.createObservableFromFetch)(request).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.mergeMap)((targetLibrary) => {
            if (window[targetLibrary.name])
                return (0,rxjs__WEBPACK_IMPORTED_MODULE_1__.of)({ targetLibrary, loadingGraph: { lock: [], fluxPacks: [], libraries: {} } });
            let libraries = {
                ...AssetsBrowserClient.appStore.project.requirements.libraries,
                ...{ [targetLibrary.name]: targetLibrary.versions[0] }
            };
            let fetchPromise = (0,_youwol_cdn_client__WEBPACK_IMPORTED_MODULE_3__.fetchBundles)(libraries, window);
            return (0,rxjs__WEBPACK_IMPORTED_MODULE_1__.from)(fetchPromise).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.map)((loadingGraph) => {
                return { targetLibrary, loadingGraph };
            }));
        }), (0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.map)(({ targetLibrary, loadingGraph }) => {
            let loaded = window[targetLibrary.name];
            return {
                factories: Object.values(loaded).filter((v) => v && v.Module && v.BuilderView),
                library: targetLibrary,
                loadingGraph
            };
        }));
    }
}
AssetsBrowserClient.appStore = undefined;
AssetsBrowserClient.tmpLibraries = undefined;
AssetsBrowserClient.urlBase = '/api/assets-gateway';
AssetsBrowserClient.urlBaseOrganisation = '/api/assets-gateway/tree';
AssetsBrowserClient.urlBaseAssets = '/api/assets-gateway/assets';
AssetsBrowserClient.urlBaseRaws = '/api/assets-gateway/raw';
AssetsBrowserClient.allGroups = undefined;
AssetsBrowserClient.headers = {};


/***/ }),

/***/ "./layout-editor/blocks.ts":
/*!*********************************!*\
  !*** ./layout-editor/blocks.ts ***!
  \*********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "getBlocks": () => (/* binding */ getBlocks)
/* harmony export */ });
function getBlocks() {
    return [
        {
            id: 'section',
            label: '<b>Section</b>',
            category: "Basic",
            attributes: { class: 'gjs-block-section' },
            content: `<section>
        <h1>This is a simple title</h1>
        <div>This is just a Lorem text: Lorem ipsum dolor sit amet</div>
      </section>`,
            render({ el }) { el.classList.add("gjs-fonts", "gjs-f-h1p"); }
        }, {
            id: 'text',
            label: 'Text',
            category: "Basic",
            content: '<div data-gjs-type="text">Insert your text here</div>',
            render({ el }) { el.classList.add("gjs-fonts", "gjs-f-text"); }
        }, {
            id: 'image',
            label: 'Image',
            category: "Basic",
            // Select the component once it's dropped
            select: true,
            // You can pass components as a JSON instead of a simple HTML string,
            // in this case we also use a defined component type `image`
            content: { type: 'image' },
            // This triggers `active` event on dropped components and the `image`
            // reacts by opening the AssetManager
            activate: true,
            render({ el }) { el.classList.add("gjs-fonts", "gjs-f-image"); }
        },
        {
            id: 'link',
            label: 'Link',
            category: "Basic",
            select: true,
            content: {
                type: 'link',
                content: 'Text for the link',
                attributes: { href: '' }
            }
        },
        {
            id: '2-columns',
            label: '2 Columns',
            category: "Layouts",
            content: `
            <div class="" style="display:flex; width:100%; height:100%; padding:5px" data-gjs-droppable=".fx-row-cell" data-gjs-custom-name="Row">
              <div class="" style="min-width:50px; width:100%" data-gjs-draggable=".row" 
                data-gjs-resizable="resizerRight" data-gjs-name= "Cell"></div>
              <div class="" style="min-width:50px; width:100%"  data-gjs-draggable=".row"
                data-gjs-resizable="resizerRight" data-gjs-name= "Cell" ></div>
            </div>
          `,
            render({ el }) { el.classList.add("gjs-fonts", "gjs-f-b2"); }
        } /*,
        {
          id: 'Youwol',
          label: 'Youwol',
          category:"Layouts",
          content: `
                <div class="row vh-100" data-gjs-droppable=".row-cell" data-gjs-custom-name="Row">
                  <div class="row-cell w-25 px-3 background-primary text-white" data-gjs-draggable=".row"
                    data-gjs-resizable="resizerRight" data-gjs-name= "Cell">
    
                    <img data-gjs-type="image" draggable="true" src="api/cdn-backend/assets/logo_YouWol_Platform_white.png" class="w-50" id="ittd" class="logo gjs-hovered">
    
                    <div class="h-separator my-3">  </div>
                    <h4 class="text-center " > Title </h4>
                    
                    <div class="my-4">
                      <p class="lead text-justify"><em> This is some description </em></p>
                    </div>
                    <div class="h-separator  my-2">  </div>
                    <div class="mt-4">
                      <p  class="text-justify" > Some content </p>
                    </div>
                  </div>
                  <div class="row-cell w-75" data-gjs-draggable=".row"
                    data-gjs-resizable="resizerRight" data-gjs-name= "Cell"></div>
                </div>
                <style>
                  .logo{
                    width:100%
                  }
                  .h-separator{
                    background-color: white;
                    padding:1px;
                    display: block
                  }
                  .row {
                    display: flex;
                    justify-content: flex-start;
                    align-items: stretch;
                    flex-wrap: nowrap;
                    padding: 10px;
                    min-height: 75px;
                  }
                  .row-cell {
                    flex-grow: 1;
                    padding: 5px;
                  }
                </style>
              `,
          render( {el}:{el:any}) {
            let div =document.createElement("div")
            div.classList.add("v-flex")
            div.innerHTML =` <img data-gjs-type="image" draggable="true" src="/api/cdn-backend/assets/logo_YouWol_Platform_white.png" class="w-50" id="ittd" class="logo gjs-hovered">`
            el.appendChild(div) }
        }*/
    ];
}


/***/ }),

/***/ "./layout-editor/code-editors.ts":
/*!***************************************!*\
  !*** ./layout-editor/code-editors.ts ***!
  \***************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "buildCodeEditor": () => (/* binding */ buildCodeEditor),
/* harmony export */   "buildCodePanel": () => (/* binding */ buildCodePanel)
/* harmony export */ });
/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./utils */ "./layout-editor/utils.ts");

function buildCodeEditor(editor, type) {
    var codeEditor = editor.CodeManager.getViewer('CodeMirror').clone();
    codeEditor.set({
        codeName: type === 'html' ? 'htmlmixed' : 'css',
        readOnly: false,
        theme: 'hopscotch',
        autoBeautify: true,
        autoCloseTags: true,
        autoCloseBrackets: true,
        styleActiveLine: true,
        smartIndent: true,
    });
    return codeEditor;
}
function setupHtmlAutoUpdates(appStore, editor, htmlCodeEditor) {
    function update() {
        const htmlCode = htmlCodeEditor.editor.getValue();
        if (!htmlCode)
            return;
        editor.setComponents(htmlCode);
        (0,_utils__WEBPACK_IMPORTED_MODULE_0__.replaceTemplateElements)(appStore.project.workflow.modules.map(m => m.moduleId), editor, appStore);
        let style = Object.values(editor.fluxCache).reduce((acc, cache) => acc + " " + cache.styles, "");
        editor.getStyle().add(style);
    }
    var delay;
    htmlCodeEditor.editor.on('change', function () {
        clearTimeout(delay);
        delay = setTimeout(update, 300);
    });
    htmlCodeEditor.editor.refresh();
}
function setupCssAutoUpdates(editor, cssCodeEditor) {
    function update() {
        const cssCode = cssCodeEditor.editor.getValue();
        if (!cssCode)
            return;
        editor.setStyle(cssCode);
    }
    var delay;
    cssCodeEditor.editor.on('change', function () {
        clearTimeout(delay);
        delay = setTimeout(update, 300);
    });
}
function buildCodePanel(appStore, editor, panel) {
    const codePanel = document.createElement('div');
    codePanel.classList.add('code-panel');
    const htmlSection = document.createElement('section');
    const cssSection = document.createElement('section');
    htmlSection.innerHTML = '<div>HTML</div>';
    cssSection.innerHTML = '<div>CSS</div>';
    const htmlCodeEditor = buildCodeEditor(editor, 'html');
    const cssCodeEditor = buildCodeEditor(editor, 'css');
    const htmlTextArea = document.createElement('textarea');
    const cssTextArea = document.createElement('textarea');
    htmlSection.appendChild(htmlTextArea);
    cssSection.appendChild(cssTextArea);
    codePanel.appendChild(htmlSection);
    codePanel.appendChild(cssSection);
    panel.set('appendContent', codePanel).trigger('change:appendContent');
    htmlCodeEditor.init(htmlTextArea);
    cssCodeEditor.init(cssTextArea);
    htmlCodeEditor.setContent(editor.getHtml());
    cssCodeEditor.setContent(editor.getCss({ avoidProtected: true }));
    /*Split([htmlSection, cssSection], {
      direction: 'vertical',
      sizes: [50, 50],
      minSize: 100,
      gutterSize: 2,
      onDragEnd: () => {
        htmlCodeEditor.editor.refresh();
        cssCodeEditor.editor.refresh();
      }
    });
  */
    setupHtmlAutoUpdates(appStore, editor, htmlCodeEditor);
    setupCssAutoUpdates(editor, cssCodeEditor);
    // make sure editor is aware of width change after the 300ms effect ends
    setTimeout(() => {
        htmlCodeEditor.editor.refresh();
        cssCodeEditor.editor.refresh();
    }, 320);
    return codePanel;
}


/***/ }),

/***/ "./layout-editor/commands.ts":
/*!***********************************!*\
  !*** ./layout-editor/commands.ts ***!
  \***********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "plugCommands": () => (/* binding */ plugCommands)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ../builder-editor/builder-state/index */ "./builder-editor/builder-state/index.ts");
/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./utils */ "./layout-editor/utils.ts");
/* harmony import */ var _editor__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./editor */ "./layout-editor/editor.ts");
/* harmony import */ var _code_editors__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./code-editors */ "./layout-editor/code-editors.ts");





function plugCommands(editor, appStore) {
    let debugSingleton = _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_1__.AppDebugEnvironment.getInstance();
    editor.on('change:changesCount', (e) => {
        if (appStore.project.runnerRendering.layout !== localStorage.getItem("gjs-html"))
            appStore.setRenderingLayout(localStorage.getItem("gjs-html"), false);
        let css = (0,_utils__WEBPACK_IMPORTED_MODULE_2__.cleanCss)(localStorage.getItem("gjs-css"));
        if (appStore.project.runnerRendering.style !== css)
            appStore.setRenderingStyle(css, false);
    });
    editor.on('canvas:drop', (dataTransfer, component) => {
        debugSingleton.debugOn &&
            debugSingleton.logRenderTopic({ level: _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_1__.LogLevel.Info, message: "canvas:drop", object: { dataTransfer, component: component.toJSON() } });
        let child = component.view.el;
        // it happens that grapes add suffix e.g. ('-1', '-2', etc) on id...this is a patch to recover the module
        // it is happenning when multiple rendering div of the same module in the page
        let mdle = appStore.getModule(child.id); // || appStore.getModule( child.id.split("-").slice(0,-1).join('-') )
        if (mdle) {
            debugSingleton.debugOn &&
                debugSingleton.logRenderTopic({ level: _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_1__.LogLevel.Info, message: "canvas:drop => flux-module", object: { module: mdle } });
            let childrenModulesId = [];
            if (mdle instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Component.Module && !editor.fluxCache[mdle.moduleId]) {
                (0,_utils__WEBPACK_IMPORTED_MODULE_2__.updateFluxCache)(appStore, editor);
            }
            if (mdle instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Component.Module /*&& ! editor.fluxCache[mdle.moduleId] !=component*/) {
                // in a case of Component.Module we want to recover the last created gjs-component corresponding to the flux-component
                let parent = component.parent();
                let index = parent.components().indexOf(component);
                let cached = editor.fluxCache[mdle.moduleId]; //.toHTML()
                debugSingleton.debugOn &&
                    debugSingleton.logRenderTopic({
                        level: _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_1__.LogLevel.Info, message: "canvas:drop => restore cached component",
                        object: { module: mdle, cachedComponent: cached, parent: parent.getEl() }
                    });
                component.remove();
                parent.append(cached.layout, { at: index });
                editor.getStyle().add(cached.styles);
                childrenModulesId = mdle.getAllChildren().map(m => m.moduleId);
            }
            child.id = mdle.moduleId;
            (0,_utils__WEBPACK_IMPORTED_MODULE_2__.replaceTemplateElements)([child.id, ...childrenModulesId], editor, appStore);
            (0,_editor__WEBPACK_IMPORTED_MODULE_3__.setDynamicComponentsBlocks)(appStore, editor);
        }
        (0,_utils__WEBPACK_IMPORTED_MODULE_2__.updateFluxCache)(appStore, editor);
    });
    editor.on('component:update:content', (a) => {
        //when inner html has changed, e.g. after text changed
        setTimeout(() => (0,_utils__WEBPACK_IMPORTED_MODULE_2__.updateFluxCache)(appStore, editor), 200);
    });
    editor.on('sorter:drag:end', ({ modelToDrop, srcEl }) => {
        debugSingleton.debugOn &&
            debugSingleton.logRenderTopic({ level: _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_1__.LogLevel.Info, message: "sorter:drag:end", object: { module: modelToDrop } });
        // a drop of any component is done => do nothing as the  canvas:drop wil handle the addition
        if (typeof (modelToDrop) == "string")
            return;
        // from here: the drag end is a move => in case of flux-component the cache has the appropriate content 
        let mdle = appStore.getModule(modelToDrop.ccid);
        if (mdle && !(mdle instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Component.Module))
            (0,_utils__WEBPACK_IMPORTED_MODULE_2__.replaceTemplateElements)([mdle.moduleId], editor, appStore);
        if (mdle && mdle instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Component.Module) {
            let allGjsComponents = (0,_utils__WEBPACK_IMPORTED_MODULE_2__.getAllComponentsRec)(editor);
            if (mdle instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.Component.Module)
                (0,_utils__WEBPACK_IMPORTED_MODULE_2__.addComponentPlaceholder)(appStore, editor, allGjsComponents, mdle);
            let allChildrenModulesId = mdle.getAllChildren().map(m => m.moduleId);
            (0,_utils__WEBPACK_IMPORTED_MODULE_2__.replaceTemplateElements)([mdle.moduleId].concat(allChildrenModulesId), editor, appStore);
        }
        (0,_utils__WEBPACK_IMPORTED_MODULE_2__.updateFluxCache)(appStore, editor); // if it happens that the div.id that is going to be created is a component => do not update the cache with it (at this stage it is empty)
    });
    editor.on('component:remove', (component) => {
        (0,_editor__WEBPACK_IMPORTED_MODULE_3__.setDynamicComponentsBlocks)(appStore, editor);
    });
    editor.on('selector:add', selector => {
        selector.set('private', _utils__WEBPACK_IMPORTED_MODULE_2__.privateClasses.includes(selector.id));
    });
    editor.Commands.add('show-blocks', {
        getRowEl(editor) { return editor.getContainer().closest('#editor-row'); },
        getLayersEl(row) { return row.querySelector('#blocks'); },
        run(editor, sender) {
            const lmEl = this.getLayersEl(this.getRowEl(editor));
            lmEl.style.display = '';
        },
        stop(editor, sender) {
            const lmEl = this.getLayersEl(this.getRowEl(editor));
            lmEl.style.display = 'none';
        },
    });
    editor.Commands.add('show-styles', {
        getRowEl(editor) { return editor.getContainer().closest('#editor-row'); },
        getStyleEl(row) { return row.querySelector('#styles'); },
        run(editor, sender) {
            const smEl = this.getStyleEl(this.getRowEl(editor));
            smEl.style.display = '';
        },
        stop(editor, sender) {
            const smEl = this.getStyleEl(this.getRowEl(editor));
            smEl.style.display = 'none';
        },
    });
    ;
    editor.Commands.add('show-layers', {
        getRowEl(editor) { return editor.getContainer().closest('#editor-row'); },
        getLayersEl(row) { return row.querySelector('#layers'); },
        run(editor, sender) {
            const smEl = this.getLayersEl(this.getRowEl(editor));
            smEl.style.display = '';
        },
        stop(editor, sender) {
            const smEl = this.getLayersEl(this.getRowEl(editor));
            smEl.style.display = 'none';
        },
    });
    editor.Commands.add('show-traits', {
        getRowEl(editor) { return editor.getContainer().closest('#editor-row'); },
        getTraitsEl(row) { return row.querySelector('#traits'); },
        run(editor, sender) {
            const smEl = this.getTraitsEl(this.getRowEl(editor));
            smEl.style.display = '';
        },
        stop(editor, sender) {
            const smEl = this.getTraitsEl(this.getRowEl(editor));
            smEl.style.display = 'none';
        },
    });
    editor.Commands.add('open-code', {
        getRowEl(editor) { return editor.getContainer().closest('#editor-row'); },
        getCodeEl(row) { return row.querySelector('#codes'); },
        run: function (editor, senderBtn) {
            const pn = editor.Panels;
            const id = 'code';
            const panel = pn.getPanel(id) || pn.addPanel({ id });
            let divi = this.getCodeEl(this.getRowEl(editor));
            console.log("Code elements", divi);
            if (!this.codePanel)
                this.codePanel = (0,_code_editors__WEBPACK_IMPORTED_MODULE_4__.buildCodePanel)(appStore, editor, panel);
            console.log("Code Panel", this.codePanel);
            this.codePanel.style.display = 'block';
            divi.appendChild(this.codePanel);
            //editor.$('#panel__right_render').get(0).style.width = '35%';
            //editor.$('.gjs-cv-canvas').get(0).style.width = '65%';
        },
        stop: function (editor, senderBtn) {
            if (this.codePanel)
                this.codePanel.style.display = 'none';
            //editor.$('#panel__right_render').get(0).style.width = '15%';
            //editor.$('.gjs-cv-canvas').get(0).style.width = '85%';
        },
    });
    editor.Commands.add("custom-preview", {
        run(editor, sender) {
            document.querySelector("#gjs-cv-tools").classList.add("preview");
            editor.Canvas.getDocument().getElementById("wrapper").classList.add("preview");
            // we hide template elements
            Array.from(editor.Canvas.getDocument().querySelectorAll(".flux-builder-only"))
                .forEach((element) => element.classList.add('preview'));
            let panelsContainer = document.getElementById("panels-container-render");
            panelsContainer.classList.add("collapsed");
            let panel = document.getElementById("panel__right_render");
            panel.classList.add("collapsed");
            panel.querySelectorAll(".flex-align-switch").forEach((e) => e.style.flexDirection = "column");
            editor.$('#panel__right_render').get(0).style.width = '50px';
            panel.querySelectorAll(".buttons-toolbox").forEach((e) => {
                let div = e.firstChild;
                if (div && div.style)
                    div.style.flexDirection = "column";
            });
        },
        stop(editor, sender) {
            document.querySelector("#gjs-cv-tools").classList.remove("preview");
            editor.Canvas.getDocument().getElementById("wrapper").classList.remove("preview");
            Array.from(editor.Canvas.getDocument().querySelectorAll(".flux-builder-only"))
                .forEach((element) => element.classList.remove('preview'));
            let panelsContainer = document.getElementById("panels-container-render");
            panelsContainer.classList.remove("collapsed");
            let panel = document.getElementById("panel__right_render");
            panel.classList.remove("collapsed");
            panel.querySelectorAll(".flex-align-switch").forEach((e) => e.style.flexDirection = "row");
            //editor.$('#panel__right_render').get(0).style.width = '15%';
            panel.querySelectorAll(".buttons-toolbox").forEach((e) => {
                let div = e.firstChild;
                if (div && div.style)
                    div.style.flexDirection = "row";
            });
        }
    });
    editor.Commands.add('set-device-tablet', {
        run(editor, sender) {
            editor.setDevice('Tablet');
        },
        stop(editor, sender) { },
    });
    editor.Commands.add('set-device-desktop', {
        run(editor, sender) {
            editor.setDevice('Desktop');
        },
        stop(editor, sender) { },
    });
    editor.Commands.add('set-device-mobile-landscape', {
        run(editor, sender) {
            editor.setDevice('Mobile landscape');
        },
        stop(editor, sender) { },
    });
    editor.Commands.add('set-device-mobile-portrait', {
        run(editor, sender) {
            editor.setDevice('Mobile portrait');
        },
        stop(editor, sender) { },
    });
    editor.on('run:preview:before', ({ sender }) => {
        sender.panelRight = document.getElementById("panel__right");
        sender.panelRight.remove();
    });
    editor.on('stop:preview:before', ({ sender }) => {
        if (sender && sender.panelRight) {
            document.getElementById("editor-row").appendChild(sender.panelRight);
        }
    });
}


/***/ }),

/***/ "./layout-editor/editor.ts":
/*!*********************************!*\
  !*** ./layout-editor/editor.ts ***!
  \*********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "createLayoutEditor": () => (/* binding */ createLayoutEditor),
/* harmony export */   "initLayoutEditor": () => (/* binding */ initLayoutEditor),
/* harmony export */   "setDynamicComponentsBlocks": () => (/* binding */ setDynamicComponentsBlocks)
/* harmony export */ });
/* harmony import */ var _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../builder-editor/builder-state/index */ "./builder-editor/builder-state/index.ts");
/* harmony import */ var _panels__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./panels */ "./layout-editor/panels.ts");
/* harmony import */ var _top_banner_panels__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ../top-banner/panels */ "./top-banner/panels.ts");
/* harmony import */ var _top_banner_commands__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ../top-banner/commands */ "./top-banner/commands.ts");
/* harmony import */ var _blocks__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./blocks */ "./layout-editor/blocks.ts");
/* harmony import */ var _style_manager__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./style-manager */ "./layout-editor/style-manager.ts");
/* harmony import */ var _commands__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! ./commands */ "./layout-editor/commands.ts");
/* harmony import */ var _builder_editor_commands__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! ../builder-editor/commands */ "./builder-editor/commands.ts");
/* harmony import */ var _builder_editor_panels__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(/*! ../builder-editor/panels */ "./builder-editor/panels.ts");
/* harmony import */ var _patches__WEBPACK_IMPORTED_MODULE_9__ = __webpack_require__(/*! ./patches */ "./layout-editor/patches.ts");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_10__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_10___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_10__);
/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_11__ = __webpack_require__(/*! ./utils */ "./layout-editor/utils.ts");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_12__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_12___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_12__);
/* harmony import */ var grapesjs__WEBPACK_IMPORTED_MODULE_13__ = __webpack_require__(/*! grapesjs */ "grapesjs");
/* harmony import */ var grapesjs__WEBPACK_IMPORTED_MODULE_13___default = /*#__PURE__*/__webpack_require__.n(grapesjs__WEBPACK_IMPORTED_MODULE_13__);














async function createLayoutEditor() {
    localStorage.setItem("gjs-components", "");
    localStorage.setItem("gjs-html", "");
    localStorage.setItem("gjs-css", "");
    localStorage.setItem("gjs-styles", "");
    let debugSingleton = _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
    debugSingleton.debugOn &&
        debugSingleton.logRenderTopic({
            level: _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
            message: "create layout editor",
            object: {}
        });
    let editor$ = new rxjs__WEBPACK_IMPORTED_MODULE_10__.Subject();
    let editor = grapesjs__WEBPACK_IMPORTED_MODULE_13__.init({
        autorender: false,
        container: '#gjs',
        canvas: {
            styles: [],
            scripts: []
        },
        height: '100%',
        width: 'auto',
        panels: { defaults: [] },
        assetManager: {
            assets: [],
            autoAdd: 1
        },
        keymaps: {
            defaults: {} // remove default keymaps - especially to remove delete map
        },
        commands: {
            defaults: []
        },
        selectorManager: {
            appendTo: '#styles'
        },
        blockManager: {
            appendTo: '#blocks',
            blocks: (0,_blocks__WEBPACK_IMPORTED_MODULE_4__.getBlocks)()
        },
        styleManager: {
            appendTo: '#styles',
            sectors: (0,_style_manager__WEBPACK_IMPORTED_MODULE_5__.getStylesSectors)()
        },
        layerManager: { appendTo: '#layers', },
        traitManager: { appendTo: '#traits', },
    });
    editor.dynamicModulesId = [];
    editor.fluxCache = {};
    let bootstrapCss = document.getElementById("bootstrap-css");
    if (!bootstrapCss)
        console.error("Bootstrap css needs to be included in host application with id 'bootstrap-css' ");
    let fontawesomeCss = document.getElementById("fontawesome-css");
    if (!fontawesomeCss)
        console.error("Fontawesome css needs to be included in host application with id 'fontawesome-css' ");
    let youwolCss = document.getElementById("youwol-css");
    if (!youwolCss)
        console.error("Fontawesome css needs to be included in host application with id 'fontawesome-css' ");
    editor.on('load', function () {
        let document = editor.Canvas.getDocument();
        let headElement = document.head;
        headElement.appendChild(bootstrapCss.cloneNode());
        headElement.appendChild(fontawesomeCss.cloneNode());
        headElement.appendChild(youwolCss.cloneNode());
        var node = document.createElement('style');
        node.innerHTML = `.mw-50px{ min-width:50px}.w-5{width:5%};.w-10{width:10%}.w-15{width:15%}.w-20{width:20%}.w-30{width:30%}.w-40{width:40%}.w-60{width:60%}.w-70{width:70%}.w-80{width:80%}.w-90{width:90%}.zindex-1{z-index:1}
    .flux-component{min-height:50px;} .preview .gjs-hovered{outline:0px !important} .preview .gjs-selected{outline:0px !important} 
    .flux-builder-only{opacity:0.5} .flux-builder-only.preview{ display:none}
    .flux-fill-parent{width:100%; height:100%}`;
        document.body.appendChild(node);
        editor$.next(editor);
        editor.SelectorManager.getAll().each(selector => selector.set('private', _utils__WEBPACK_IMPORTED_MODULE_11__.privateClasses.includes(selector.id)));
    });
    editor.render();
    return new Promise((successCb) => editor$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_12__.take)(1)).subscribe((edtr) => successCb(edtr)));
}
function initLayoutEditor(editor, { style, layout, cssLinks }, appStore) {
    let debugSingleton = _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
    debugSingleton.debugOn &&
        debugSingleton.logRenderTopic({
            level: _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
            message: "initialize layout editor",
            object: {}
        });
    (0,_commands__WEBPACK_IMPORTED_MODULE_6__.plugCommands)(editor, appStore);
    let builderCommands = (0,_builder_editor_commands__WEBPACK_IMPORTED_MODULE_7__.commandsBuilder)().concat((0,_top_banner_commands__WEBPACK_IMPORTED_MODULE_3__.commandsGeneral)(appStore, editor));
    builderCommands.forEach(c => editor.Commands.add(c[0], c[1]));
    editor.BlockManager.getCategories().each((ctg) => ctg.set('open', false));
    let panels = [...(0,_top_banner_panels__WEBPACK_IMPORTED_MODULE_2__.getGeneralPanels)(appStore), ...(0,_panels__WEBPACK_IMPORTED_MODULE_1__.getRenderPanels)(), ...(0,_builder_editor_panels__WEBPACK_IMPORTED_MODULE_8__.getBuilderPanels)()];
    panels.forEach(p => editor.Panels.addPanel(p));
    (0,_patches__WEBPACK_IMPORTED_MODULE_9__.applyPatches)(editor);
    (0,_utils__WEBPACK_IMPORTED_MODULE_11__.updateFluxCache)(appStore, editor);
    editor.SelectorManager.getAll().each(selector => selector.set('private', _utils__WEBPACK_IMPORTED_MODULE_11__.privateClasses.includes(selector.id)));
    editor.setComponents(layout);
    editor.setStyle(style);
}
function scaleSvgIcons(g) {
    if (g.style.transform)
        return;
    let parentBRect = g.parentElement.getBoundingClientRect();
    let bRect = g.getBoundingClientRect();
    let ty = parentBRect.top - bRect.top;
    let tx = parentBRect.left - bRect.left;
    let scale = Math.min(parentBRect.width / bRect.width, parentBRect.height / bRect.height);
    g.style.transform = `translate(${parentBRect.width / 4}px,${parentBRect.height / 4}px) scale(${0.5 * scale}) translate(${tx}px,${ty}px)`;
}
function setDynamicComponentsBlocks(appStore, editor) {
    let debugSingleton = _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
    let all = (0,_utils__WEBPACK_IMPORTED_MODULE_11__.getAllComponentsRec)(editor);
    let layerModuleIds = appStore.getActiveLayer().moduleIds;
    let pluginIds = appStore.project.workflow.plugins
        .filter(plugin => layerModuleIds.includes(plugin.parentModule.moduleId))
        .map(plugin => plugin.moduleId);
    let modulesToRender = [...layerModuleIds, ...pluginIds]
        .filter(mid => !all[mid])
        .map(mid => appStore.getModule(mid)).filter(m => m.Factory.RenderView);
    let componentBlocks = editor.BlockManager.getAll().filter(block => block.get('category').id == "Components");
    debugSingleton.debugOn &&
        debugSingleton.logRenderTopic({
            level: _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
            message: "set dynamic components block",
            object: { modulesToRender, componentBlocks }
        });
    componentBlocks.forEach(block => editor.BlockManager.remove(block.id));
    modulesToRender.forEach(m => editor.BlockManager.add(m.moduleId, toDynamicBlock(m)));
}
function toDynamicBlock(mdle) {
    return {
        id: mdle.moduleId,
        label: mdle.configuration.title,
        content: (0,_utils__WEBPACK_IMPORTED_MODULE_11__.getDynamicBlockWrapperDiv)(mdle),
        activate: true,
        category: "Components",
        render: ({ el }) => {
            let div = document.createElement("div");
            div.id = mdle.moduleId;
            el.appendChild(div);
            let svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.setAttribute("width", "100px");
            svg.setAttribute("height", "70px");
            let item = new mdle.Factory.BuilderView().icon();
            const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
            g.style.stroke = "currentColor";
            g.classList.add("group-target");
            g.innerHTML = item.content;
            svg.appendChild(g);
            div.appendChild(svg);
            document.body.appendChild(svg);
            scaleSvgIcons(g);
            svg.remove();
            div.appendChild(svg);
        }
    };
}


/***/ }),

/***/ "./layout-editor/index.ts":
/*!********************************!*\
  !*** ./layout-editor/index.ts ***!
  \********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "getBlocks": () => (/* reexport safe */ _blocks__WEBPACK_IMPORTED_MODULE_0__.getBlocks),
/* harmony export */   "buildCodeEditor": () => (/* reexport safe */ _code_editors__WEBPACK_IMPORTED_MODULE_1__.buildCodeEditor),
/* harmony export */   "buildCodePanel": () => (/* reexport safe */ _code_editors__WEBPACK_IMPORTED_MODULE_1__.buildCodePanel),
/* harmony export */   "plugCommands": () => (/* reexport safe */ _commands__WEBPACK_IMPORTED_MODULE_2__.plugCommands),
/* harmony export */   "createLayoutEditor": () => (/* reexport safe */ _editor__WEBPACK_IMPORTED_MODULE_3__.createLayoutEditor),
/* harmony export */   "initLayoutEditor": () => (/* reexport safe */ _editor__WEBPACK_IMPORTED_MODULE_3__.initLayoutEditor),
/* harmony export */   "setDynamicComponentsBlocks": () => (/* reexport safe */ _editor__WEBPACK_IMPORTED_MODULE_3__.setDynamicComponentsBlocks),
/* harmony export */   "getRenderPanels": () => (/* reexport safe */ _panels__WEBPACK_IMPORTED_MODULE_4__.getRenderPanels),
/* harmony export */   "applyPatches": () => (/* reexport safe */ _patches__WEBPACK_IMPORTED_MODULE_5__.applyPatches),
/* harmony export */   "getJsRessources": () => (/* reexport safe */ _resources_initialisation__WEBPACK_IMPORTED_MODULE_6__.getJsRessources),
/* harmony export */   "getStylesSectors": () => (/* reexport safe */ _style_manager__WEBPACK_IMPORTED_MODULE_7__.getStylesSectors),
/* harmony export */   "addComponentPlaceholder": () => (/* reexport safe */ _utils__WEBPACK_IMPORTED_MODULE_8__.addComponentPlaceholder),
/* harmony export */   "autoAddElementInLayout": () => (/* reexport safe */ _utils__WEBPACK_IMPORTED_MODULE_8__.autoAddElementInLayout),
/* harmony export */   "cleanCss": () => (/* reexport safe */ _utils__WEBPACK_IMPORTED_MODULE_8__.cleanCss),
/* harmony export */   "getAllComponentsRec": () => (/* reexport safe */ _utils__WEBPACK_IMPORTED_MODULE_8__.getAllComponentsRec),
/* harmony export */   "getDynamicBlockWrapperDiv": () => (/* reexport safe */ _utils__WEBPACK_IMPORTED_MODULE_8__.getDynamicBlockWrapperDiv),
/* harmony export */   "privateClasses": () => (/* reexport safe */ _utils__WEBPACK_IMPORTED_MODULE_8__.privateClasses),
/* harmony export */   "removeTemplateElements": () => (/* reexport safe */ _utils__WEBPACK_IMPORTED_MODULE_8__.removeTemplateElements),
/* harmony export */   "replaceTemplateElements": () => (/* reexport safe */ _utils__WEBPACK_IMPORTED_MODULE_8__.replaceTemplateElements),
/* harmony export */   "updateFluxCache": () => (/* reexport safe */ _utils__WEBPACK_IMPORTED_MODULE_8__.updateFluxCache)
/* harmony export */ });
/* harmony import */ var _blocks__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./blocks */ "./layout-editor/blocks.ts");
/* harmony import */ var _code_editors__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./code-editors */ "./layout-editor/code-editors.ts");
/* harmony import */ var _commands__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./commands */ "./layout-editor/commands.ts");
/* harmony import */ var _editor__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./editor */ "./layout-editor/editor.ts");
/* harmony import */ var _panels__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ./panels */ "./layout-editor/panels.ts");
/* harmony import */ var _patches__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./patches */ "./layout-editor/patches.ts");
/* harmony import */ var _resources_initialisation__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! ./resources-initialisation */ "./layout-editor/resources-initialisation.ts");
/* harmony import */ var _style_manager__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! ./style-manager */ "./layout-editor/style-manager.ts");
/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(/*! ./utils */ "./layout-editor/utils.ts");











/***/ }),

/***/ "./layout-editor/panels.ts":
/*!*********************************!*\
  !*** ./layout-editor/panels.ts ***!
  \*********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "getRenderPanels": () => (/* binding */ getRenderPanels)
/* harmony export */ });
function getRenderPanels() {
    return [
        {
            id: 'layout-basic-actions',
            el: '#panel__layout-basic-actions',
            buttons: [
                {
                    id: 'visibility',
                    active: true,
                    className: 'btn-toggle-borders',
                    label: '<i class="fas fa-border-none"></i>',
                    command: 'sw-visibility', // Built-in command
                }
            ],
        }, {
            id: 'layout-show-actions',
            el: '#panel__render-show-actions',
            buttons: [
                {
                    id: 'preview',
                    className: 'btn-preview',
                    label: '<i class="fas fa-eye"></i>',
                    command: 'custom-preview', // Built-in command
                }
            ],
        }, {
            id: 'layout-devices-actions',
            el: '#panel__layout-devices-actions',
            buttons: [
                {
                    id: 'desktop',
                    active: true,
                    className: 'btn-set-device-desktop',
                    label: '<i class="fas fa-desktop"></i>',
                    command: 'set-device-desktop'
                },
                {
                    id: 'tablet',
                    active: false,
                    className: 'btn-set-device-tablet',
                    label: '<i class="fas fa-tablet-alt"></i>',
                    command: 'set-device-tablet'
                },
                {
                    id: 'mobile landscape',
                    active: false,
                    className: 'btn-set-device-phone',
                    label: '<i class="fas fa-mobile-alt"></i>',
                    command: 'set-device-mobile-landscape'
                },
                {
                    id: 'mobile portrait',
                    active: false,
                    className: 'btn-set-device-phone',
                    label: '<i class="fas fa-mobile-alt"></i>',
                    command: 'set-device-mobile-portrait'
                }
            ],
        },
        {
            id: 'layout-managers-actions',
            el: '#panel__render-panels-actions',
            buttons: [{
                    id: 'show-blocks',
                    active: true,
                    label: '<i class="fas fa-th-large"></i>',
                    command: 'show-blocks',
                    // Once activated disable the possibility to turn it off
                    togglable: false,
                },
                {
                    id: 'show-style',
                    active: false,
                    label: '<i class="fas fa-palette"></i>',
                    command: 'show-styles',
                    togglable: false,
                },
                {
                    id: 'show-traits',
                    active: false,
                    className: 'fa fa-cog',
                    command: 'show-traits',
                    attributes: { title: 'Open Trait Manager' },
                    togglable: false,
                },
                {
                    id: 'show-layers',
                    active: false,
                    className: 'fa fa-bars',
                    command: 'show-layers',
                    attributes: { title: 'Open Layer Manager' },
                    togglable: false,
                },
                {
                    id: 'code',
                    className: 'btn-preview',
                    label: '<i class="fas fa-code"></i>',
                    command: 'open-code', // Built-in command
                }]
        }
    ];
    /*
    editor.Panels.addPanel({
        id: 'layers',
        el: '.panel__right',
        // Make the panel resizable
        resizable: {
          maxDim: 350,
          minDim: 200,
          tc: 0, // Top handler
          cl: 1, // Left handler
          cr: 0, // Right handler
          bc: 0, // Bottom handler
          // Being a flex child we need to change `flex-basis` property
          // instead of the `width` (default)
          keyWidth: 'flex-basis',
        },
      })*/
}


/***/ }),

/***/ "./layout-editor/patches.ts":
/*!**********************************!*\
  !*** ./layout-editor/patches.ts ***!
  \**********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "applyPatches": () => (/* binding */ applyPatches)
/* harmony export */ });
function applyPatches(editor) {
    /**
     * This patch is to switch between old fontawesome icons to corresponding new ones
     */
    let toolbarDiv = document.getElementById("gjs-tools").querySelector(".gjs-toolbar");
    const callback = function (mutationsList, observer) {
        if (toolbarDiv.children.length > 0) {
            toolbarDiv.querySelector(".fa-arrows").classList.add("fas", "fa-arrows-alt");
            toolbarDiv.querySelector(".fa-trash-o").classList.add("fas", "fa-trash");
        }
    };
    const observer = new MutationObserver(callback);
    observer.observe(toolbarDiv, { attributes: true, childList: true, subtree: false });
    /** the default move command is patched such that it is allow to drag only  if
     * the dedicated 'move' icon is used. Mixing dragging inside the component w/ layout change + internal
     * component behavior was causing problem
     */
    let defaultMove = editor.Commands.get('tlb-move');
    editor.Commands.add('tlb-move', {
        run(ed, sender, opts = {}) {
            /* If the dedicated icon is used => opts["event"].target is not defined */
            if (opts && opts["event"] && opts["event"].target)
                return;
            defaultMove.run(ed, sender, opts);
        }
    });
    /* --- Those next four lines are hacky, it ensure the attributes and styles panels are not displayed at first
    This problem seems to occur only for light workflow
    -----*/
    editor.Commands.run("show-attributes");
    editor.Commands.stop("show-attributes");
    editor.Commands.run("show-styles");
    editor.Commands.stop("show-styles");
    editor.Commands.run("show-traits");
    editor.Commands.stop("show-traits");
    editor.Commands.run("show-layers");
    editor.Commands.stop("show-layers");
    /*editor.Commands.run("show-suggestions")
    editor.Commands.stop("show-suggestions")
    editor.Commands.run("show-extensions")
    editor.Commands.stop("show-extensions")*/
    /* ---
    ---*/
    let buttons_container = document.getElementById("panel__builder-managers-actions").children[0];
    buttons_container.classList.add("d-flex", "flex-wrap");
    let buttons_container2 = document.getElementById("panel__layout-devices-actions").children[0];
    buttons_container2.classList.add("d-flex", "flex-wrap");
    let buttons_container3 = document.getElementById("panel__render-panels-actions").children[0];
    buttons_container3.classList.add("d-flex", "flex-wrap");
    let buttons_container4 = document.getElementById("panel__builder-actions-items").children[0];
    buttons_container4.classList.add("d-flex", "flex-wrap");
}


/***/ }),

/***/ "./layout-editor/resources-initialisation.ts":
/*!***************************************************!*\
  !*** ./layout-editor/resources-initialisation.ts ***!
  \***************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "getJsRessources": () => (/* binding */ getJsRessources)
/* harmony export */ });
function getJsRessources(appStore) {
    return appStore.packages.reduce((acc, pack) => {
        let js = pack.requirements
            .filter(r => r.type === "javascript-external")
            .map(r => r.src);
        return acc.concat(js);
    }, []);
}


/***/ }),

/***/ "./layout-editor/style-manager.ts":
/*!****************************************!*\
  !*** ./layout-editor/style-manager.ts ***!
  \****************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "getStylesSectors": () => (/* binding */ getStylesSectors)
/* harmony export */ });
function getStylesSectors() {
    return [{
            name: 'Dimension',
            open: false,
            // Use built-in properties
            buildProps: ['width', 'height', 'min-width', 'min-height', 'max-width', 'max-height', 'padding', 'margin'],
            // Use `properties` to define/override single property
            properties: [
                {
                    // Type of the input,
                    // options: integer | radio | select | color | slider | file | composite | stack
                    type: 'integer',
                    name: 'The width',
                    property: 'width',
                    units: ['px', '%'],
                    defaults: 'auto',
                    min: 0, // Min value, available only for 'integer' types
                }
            ]
        }, {
            name: 'Extra',
            open: false,
            buildProps: ['background-color', 'box-shadow', 'custom-prop'],
            properties: [
                {
                    id: 'custom-prop',
                    name: 'Custom Label',
                    property: 'font-size',
                    type: 'select',
                    defaults: '32px',
                    // List of options, available only for 'select' and 'radio'  types
                    options: [
                        { value: '12px', name: 'Tiny' },
                        { value: '18px', name: 'Medium' },
                        { value: '32px', name: 'Big' },
                    ],
                }
            ]
        }, {
            name: 'Typography',
            open: false,
            buildProps: ['font-family', 'font-size', 'font-weight', 'letter-spacing', 'color', 'line-height', 'text-align', 'text-decoration', 'text-shadow'],
            properties: [
                { name: 'Font', property: 'font-family' },
                { name: 'Weight', property: 'font-weight' },
                { name: 'Font color', property: 'color' },
                {
                    property: 'text-align',
                    type: 'radio',
                    defaults: 'left',
                    list: [
                        { value: 'left', name: 'Left', className: 'fa fa-align-left' },
                        { value: 'center', name: 'Center', className: 'fa fa-align-center' },
                        { value: 'right', name: 'Right', className: 'fa fa-align-right' },
                        { value: 'justify', name: 'Justify', className: 'fa fa-align-justify' }
                    ],
                }, {
                    property: 'text-decoration',
                    type: 'radio',
                    defaults: 'none',
                    list: [
                        { value: 'none', name: 'None', className: 'fa fa-times' },
                        { value: 'underline', name: 'underline', className: 'fa fa-underline' },
                        { value: 'line-through', name: 'Line-through', className: 'fa fa-strikethrough' }
                    ],
                }, {
                    property: 'text-shadow',
                    properties: [
                        { name: 'X position', property: 'text-shadow-h' },
                        { name: 'Y position', property: 'text-shadow-v' },
                        { name: 'Blur', property: 'text-shadow-blur' },
                        { name: 'Color', property: 'text-shadow-color' }
                    ],
                }
            ],
        }, {
            name: 'Decorations',
            open: false,
            buildProps: ['opacity', 'background-color', 'border-radius', 'border', 'box-shadow', 'background'],
            properties: [{
                    type: 'slider',
                    property: 'opacity',
                    defaults: 1,
                    step: 0.01,
                    max: 1,
                    min: 0,
                }, {
                    property: 'border-radius',
                    properties: [
                        { name: 'Top', property: 'border-top-left-radius' },
                        { name: 'Right', property: 'border-top-right-radius' },
                        { name: 'Bottom', property: 'border-bottom-left-radius' },
                        { name: 'Left', property: 'border-bottom-right-radius' }
                    ],
                }, {
                    property: 'box-shadow',
                    properties: [
                        { name: 'X position', property: 'box-shadow-h' },
                        { name: 'Y position', property: 'box-shadow-v' },
                        { name: 'Blur', property: 'box-shadow-blur' },
                        { name: 'Spread', property: 'box-shadow-spread' },
                        { name: 'Color', property: 'box-shadow-color' },
                        { name: 'Shadow type', property: 'box-shadow-type' }
                    ],
                }, {
                    property: 'background',
                    properties: [
                        { name: 'Image', property: 'background-image' },
                        { name: 'Repeat', property: 'background-repeat' },
                        { name: 'Position', property: 'background-position' },
                        { name: 'Attachment', property: 'background-attachment' },
                        { name: 'Size', property: 'background-size' }
                    ],
                },],
        }, {
            name: 'Extra',
            open: false,
            buildProps: ['transition', 'perspective', 'transform'],
            properties: [{
                    property: 'transition',
                    properties: [
                        { name: 'Property', property: 'transition-property' },
                        { name: 'Duration', property: 'transition-duration' },
                        { name: 'Easing', property: 'transition-timing-function' }
                    ],
                }, {
                    property: 'transform',
                    properties: [
                        { name: 'Rotate X', property: 'transform-rotate-x' },
                        { name: 'Rotate Y', property: 'transform-rotate-y' },
                        { name: 'Rotate Z', property: 'transform-rotate-z' },
                        { name: 'Scale X', property: 'transform-scale-x' },
                        { name: 'Scale Y', property: 'transform-scale-y' },
                        { name: 'Scale Z', property: 'transform-scale-z' }
                    ],
                }]
        }, {
            name: 'Flex',
            open: false,
            properties: [{
                    name: 'Flex Container',
                    property: 'display',
                    type: 'select',
                    defaults: 'block',
                    list: [
                        { value: 'block', name: 'Disable' },
                        { value: 'flex', name: 'Enable' }
                    ],
                }, {
                    name: 'Flex Parent',
                    property: 'label-parent-flex',
                    type: 'integer',
                }, {
                    name: 'Direction',
                    property: 'flex-direction',
                    type: 'radio',
                    defaults: 'row',
                    list: [{
                            value: 'row',
                            name: 'Row',
                            className: 'icons-flex icon-dir-row',
                            title: 'Row',
                        }, {
                            value: 'row-reverse',
                            name: 'Row reverse',
                            className: 'icons-flex icon-dir-row-rev',
                            title: 'Row reverse',
                        }, {
                            value: 'column',
                            name: 'Column',
                            title: 'Column',
                            className: 'icons-flex icon-dir-col',
                        }, {
                            value: 'column-reverse',
                            name: 'Column reverse',
                            title: 'Column reverse',
                            className: 'icons-flex icon-dir-col-rev',
                        }],
                }, {
                    name: 'Justify',
                    property: 'justify-content',
                    type: 'radio',
                    defaults: 'flex-start',
                    list: [{
                            value: 'flex-start',
                            className: 'icons-flex icon-just-start',
                            title: 'Start',
                        }, {
                            value: 'flex-end',
                            title: 'End',
                            className: 'icons-flex icon-just-end',
                        }, {
                            value: 'space-between',
                            title: 'Space between',
                            className: 'icons-flex icon-just-sp-bet',
                        }, {
                            value: 'space-around',
                            title: 'Space around',
                            className: 'icons-flex icon-just-sp-ar',
                        }, {
                            value: 'center',
                            title: 'Center',
                            className: 'icons-flex icon-just-sp-cent',
                        }],
                }, {
                    name: 'Align',
                    property: 'align-items',
                    type: 'radio',
                    defaults: 'center',
                    list: [{
                            value: 'flex-start',
                            title: 'Start',
                            className: 'icons-flex icon-al-start',
                        }, {
                            value: 'flex-end',
                            title: 'End',
                            className: 'icons-flex icon-al-end',
                        }, {
                            value: 'stretch',
                            title: 'Stretch',
                            className: 'icons-flex icon-al-str',
                        }, {
                            value: 'center',
                            title: 'Center',
                            className: 'icons-flex icon-al-center',
                        }],
                }, {
                    name: 'Flex Children',
                    property: 'label-parent-flex',
                    type: 'integer',
                }, {
                    name: 'Order',
                    property: 'order',
                    type: 'integer',
                    defaults: 0,
                    min: 0
                }, {
                    name: 'Flex',
                    property: 'flex',
                    type: 'composite',
                    properties: [{
                            name: 'Grow',
                            property: 'flex-grow',
                            type: 'integer',
                            defaults: 0,
                            min: 0
                        }, {
                            name: 'Shrink',
                            property: 'flex-shrink',
                            type: 'integer',
                            defaults: 0,
                            min: 0
                        }, {
                            name: 'Basis',
                            property: 'flex-basis',
                            type: 'integer',
                            units: ['px', '%', ''],
                            unit: '',
                            defaults: 'auto',
                        }],
                }, {
                    name: 'Align',
                    property: 'align-self',
                    type: 'radio',
                    defaults: 'auto',
                    list: [{
                            value: 'auto',
                            name: 'Auto',
                        }, {
                            value: 'flex-start',
                            title: 'Start',
                            className: 'icons-flex icon-al-start',
                        }, {
                            value: 'flex-end',
                            title: 'End',
                            className: 'icons-flex icon-al-end',
                        }, {
                            value: 'stretch',
                            title: 'Stretch',
                            className: 'icons-flex icon-al-str',
                        }, {
                            value: 'center',
                            title: 'Center',
                            className: 'icons-flex icon-al-center',
                        }],
                }]
        }
    ];
}


/***/ }),

/***/ "./layout-editor/utils.ts":
/*!********************************!*\
  !*** ./layout-editor/utils.ts ***!
  \********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "privateClasses": () => (/* binding */ privateClasses),
/* harmony export */   "cleanCss": () => (/* binding */ cleanCss),
/* harmony export */   "getAllComponentsRec": () => (/* binding */ getAllComponentsRec),
/* harmony export */   "removeTemplateElements": () => (/* binding */ removeTemplateElements),
/* harmony export */   "replaceTemplateElements": () => (/* binding */ replaceTemplateElements),
/* harmony export */   "getDynamicBlockWrapperDiv": () => (/* binding */ getDynamicBlockWrapperDiv),
/* harmony export */   "addComponentPlaceholder": () => (/* binding */ addComponentPlaceholder),
/* harmony export */   "autoAddElementInLayout": () => (/* binding */ autoAddElementInLayout),
/* harmony export */   "updateFluxCache": () => (/* binding */ updateFluxCache)
/* harmony export */ });
/* harmony import */ var _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../builder-editor/builder-state/index */ "./builder-editor/builder-state/index.ts");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__);


let privateClasses = ["flux-element", "flux-component", "flux-fill-parent"];
function cleanCss(css) {
    let rules = [...new Set(css.split("}"))].filter(r => r.length > 0).map(r => r + "}");
    return rules.reduce((acc, e) => acc + e, "");
}
function getAllComponentsRec(editor, component = undefined) {
    const getAllComponents = (model, result = []) => {
        result.push(model);
        model.components().each(mod => getAllComponents(mod, result));
        return result;
    };
    component = component || editor.DomComponents.getWrapper();
    let rList = getAllComponents(component);
    return rList.reduce((acc, e) => Object.assign({}, acc, { [e.ccid]: e }), {});
}
function removeTemplateElements(modules, editor) {
    let allGjs = getAllComponentsRec(editor);
    let modulesToRemove = modules
        .filter((m) => m.Factory.RenderView);
    let debugSingleton = _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
    debugSingleton.debugOn &&
        debugSingleton.logRenderTopic({
            level: _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
            message: `removeTemplateElements`,
            object: { modules, modulesToRemove }
        });
    modulesToRemove
        .filter(mdle => allGjs[mdle.moduleId])
        .forEach(mdle => allGjs[mdle.moduleId].remove());
}
function replaceTemplateElements(moduleIds, editor, appStore) {
    let allGjsComponents = getAllComponentsRec(editor);
    let doc = editor.Canvas.getDocument();
    let mdles = moduleIds
        .map((mid) => appStore.getModule(mid))
        .filter(mdle => mdle.Factory.RenderView);
    let elemsGenerator = mdles.map(mdle => () => new mdle.Factory.RenderView(mdle));
    let parentDivs = mdles.map((m) => doc.getElementById(m.moduleId));
    let toRender = _.zip(mdles, elemsGenerator, parentDivs)
        .filter(([, , parentDiv]) => parentDiv) // Typically when undoing a module deletion => the div is not re-inserted
        .filter(([mdle]) => !(mdle instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.Component.Module))
        .map(([mdle, generator, parentDiv]) => [mdle, parentDiv, generator().render()])
        .filter(([, , renderView]) => renderView);
    let debugSingleton = _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
    debugSingleton.debugOn &&
        debugSingleton.logRenderTopic({
            level: _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
            message: `replaceTemplateElements`,
            object: { mdles, toRender }
        });
    let rendered = toRender.map(([mdle, parentDiv, renderView]) => {
        if (parentDiv.children[0] != undefined)
            parentDiv.children[0].remove();
        parentDiv.appendChild(renderView);
        if (mdle["renderedElementDisplayed$"] && renderView) {
            mdle["renderedElementDisplayed$"].next(renderView);
        }
        return mdle;
    });
    let components = _.zip(mdles, elemsGenerator, parentDivs)
        .filter(([mdle]) => mdle instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.Component.Module);
    let getDepth = (elem, depth) => (elem == null || elem.parentNode == null) ? depth : getDepth(elem.parentNode, depth + 1);
    components
        .map(([mdle, _, div]) => [mdle, div, getDepth(div, 0)])
        .sort((a, b) => b[2] - a[2])
        .forEach(([mdle]) => {
        let renderedDiv = doc.getElementById(mdle.moduleId);
        renderedDiv && mdle["renderedElementDisplayed$"].next(renderedDiv);
    });
    mdles.forEach(mdle => allGjsComponents[mdle.moduleId] ? allGjsComponents[mdle.moduleId].attributes["name"] = mdle.configuration.title : undefined);
    if (appStore.project.runnerRendering.layout !== localStorage.getItem("gjs-html"))
        appStore.setRenderingLayout(localStorage.getItem("gjs-html"), false);
    return rendered;
}
function getDynamicBlockWrapperDiv(mdle) {
    let attr = mdle.Factory.RenderView.wrapperDivAttributes;
    let classes = `flux-element` +
        (mdle instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.Component.Module ? " flux-component" : "") +
        (attr && attr(mdle).class ? " " + attr(mdle).class : "");
    let styles = attr && attr(mdle).style ? attr(mdle).style : {};
    let styleStr = Object.entries(styles).reduce((acc, [k, v]) => acc + k + ":" + v + ";", "");
    return `<div id="${mdle.moduleId}" class="${classes}" style="${styleStr}" data-gjs-name="${mdle.configuration.title}" ></div>`;
}
function addComponentPlaceholder(appStore, editor, allGjsComponents, mdle) {
    // the component is added in the parent component corresponding to the right group, if any
    let container = appStore.getParentGroupModule(mdle.moduleId);
    let htmlContent = getDynamicBlockWrapperDiv(mdle);
    if (mdle instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.Component.Module && mdle.rendering) {
        htmlContent = mdle.rendering.layout;
        editor.getStyle().add(mdle.rendering.style);
        mdle.rendering = undefined;
    }
    if (editor.fluxCache[mdle.moduleId])
        htmlContent = editor.fluxCache[mdle.moduleId].layout;
    if (!container)
        return editor.DomComponents.getComponents().add(htmlContent, { at: 0 });
    if (allGjsComponents[container.moduleId])
        return allGjsComponents[container.moduleId].append(htmlContent, { at: 0 });
}
function autoAddElementInLayout(diff, editor, appStore) {
    let views = diff.createdElements
        .filter((mdle) => mdle.Factory.RenderView);
    let removedIds = diff.removedElements.map(m => m.moduleId);
    let news = views
        .filter((mdle) => !removedIds.includes(mdle.moduleId))
        // element are added automatically only if in the root layer
        // it also allows to handle the case of a group actually not displayed
        .filter((mdle) => appStore.project.workflow.rootLayerTree.moduleIds.includes(mdle.moduleId));
    let toReplace = views
        .filter((mdle) => removedIds.includes(mdle.moduleId));
    if (toReplace.length > 0)
        replaceTemplateElements(toReplace.map(mdle => mdle.moduleId), editor, appStore);
    if (news.length == 0)
        return;
    let allGjsComponents = getAllComponentsRec(editor);
    let modules = news.filter((mdle) => !allGjsComponents[mdle.moduleId]);
    let components = modules.filter(mdle => mdle instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.Component.Module);
    let unitModules = modules.filter(mdle => !(mdle instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.Component.Module));
    let debugSingleton = _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
    debugSingleton.debugOn &&
        debugSingleton.logRenderTopic({
            level: _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
            message: "auto add elements in layout",
            object: { unitModules, components }
        });
    unitModules.forEach((mdle) => addComponentPlaceholder(appStore, editor, allGjsComponents, mdle));
    let allChildrenId = components.reduce((acc, mdle) => acc.concat(mdle.getAllChildren().map(m => m.moduleId)), []);
    components.forEach((mdle) => {
        let parentComponent = addComponentPlaceholder(appStore, editor, allGjsComponents, mdle);
        if (!editor.fluxCache[mdle.moduleId]) {
            // if the component was not in the cache => we remove children (likely already in the wrapper div), and add them in the right gjs-component
            let childComponents = mdle.getDirectChildren().map(m => allGjsComponents[m.moduleId]).filter(elem => elem);
            childComponents.forEach(childComponent => {
                childComponent.remove();
                parentComponent.append(childComponent);
            });
        }
    });
    replaceTemplateElements(unitModules.map(mdle => mdle.moduleId).concat(allChildrenId), editor, appStore);
    updateFluxCache(appStore, editor);
}
function css(el, doc) {
    var sheets = doc.styleSheets, ret = [];
    el.matches = el.matches || el.webkitMatchesSelector || el.mozMatchesSelector
        || el.msMatchesSelector || el.oMatchesSelector;
    for (var i in sheets) {
        var rules = sheets[i].rules || sheets[i].cssRules;
        for (var r in rules) {
            if (el.matches(rules[r]["selectorText"])) {
                ret.push(rules[r].cssText);
            }
        }
    }
    return ret;
}
function updateFluxCache(appStore, editor) {
    let debugSingleton = _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
    let componentsMdle = appStore.project.workflow.modules.filter(m => m instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_1__.Component.Module);
    let gjsComponents = getAllComponentsRec(editor);
    let renderedFluxComponents = componentsMdle
        .filter(mdle => gjsComponents[mdle.moduleId]);
    let update = renderedFluxComponents
        .reduce((acc, e) => {
        let styles = {}; /*Object.values(getAllComponentsRec(editor, gjsComponents[e.moduleId]))
        .map( (c:any) => c.getEl() )
        .filter(el=> el && el.matches)
        .map( el => css(el, editor.Canvas.getDocument() ))
        .reduce( (acc,e)=> acc.concat(e),[])
        .filter( e => e[0]=="#" )
        .reduce( (acc,e)=> acc+" "+e,"")*/
        let layout = gjsComponents[e.moduleId].toHTML();
        return Object.assign({}, acc, { [e.moduleId]: { layout, styles } });
    }, editor.fluxCache);
    editor.fluxCache = Object.assign({}, editor.fluxCache, update);
    debugSingleton.debugOn &&
        debugSingleton.logRenderTopic({
            level: _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info,
            message: "updateFluxCache",
            object: { cache: editor.fluxCache }
        });
}


/***/ }),

/***/ "./notification.ts":
/*!*************************!*\
  !*** ./notification.ts ***!
  \*************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "plugNotifications": () => (/* binding */ plugNotifications),
/* harmony export */   "Notifier": () => (/* binding */ Notifier)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @youwol/flux-view */ "@youwol/flux-view");
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var _builder_editor_views_context_view__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./builder-editor/views/context.view */ "./builder-editor/views/context.view.ts");




/**
 * Focus a module in the workflow by toggeling a provided class on the module's svg group element for
 * a provided duration. Focusing means:
 * -    the active layer is changed to the mdoule's containing layer if need be
 * -    the builder canvas is translated such that the module is located at its center
 * -    if styles are associated to the toggeling class, those are applied during the specified duration
 *
 * @param mdle module to focus
 * @param appStore reference to the appStore of the application
 * @param workflowPlotter reference to the workflow plotter of the application
 * @param toggledClass name of the toggeling class
 * @param duration duration of the focus
 */
function focusAction(mdle, appStore, workflowPlotter, toggledClass, duration = 5000) {
    let root = appStore.project.workflow.rootLayerTree;
    let layer = root.getLayerRecursive((layer) => layer.moduleIds.includes(mdle.moduleId));
    appStore.selectActiveLayer(layer.layerId);
    setTimeout(() => {
        let g = document.getElementById(mdle.moduleId);
        let bBox = g.getBoundingClientRect();
        workflowPlotter.drawingArea.lookAt(0.5 * (bBox.left + bBox.right), 0.5 * (bBox.top + bBox.bottom));
        g.classList.toggle(toggledClass);
        setTimeout(() => g.classList.toggle(toggledClass), duration);
    }, 0);
}
/**
 * Plug the notification system to the application environment.
 * For now, only module's errors (ModuleError in flux-core) are handled.
 *
 * @param appStore reference to the appStore of the application
 * @param workflowPlotter reference to the workflow plotter of the application
 */
function plugNotifications(appStore, workflowPlotter) {
    appStore.environment.errors$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.filter)((log) => log.error instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ModuleError)).subscribe((log) => Notifier.error({
        message: log.error.message,
        title: log.error.module.Factory.id,
        actions: [
            {
                name: 'focus',
                exe: () => focusAction(log.error.module, appStore, workflowPlotter, "error")
            },
            {
                name: 'report',
                exe: () => _builder_editor_views_context_view__WEBPACK_IMPORTED_MODULE_3__.ContextView.reportContext(log.context, log.id)
            }
        ]
    }));
    appStore.environment.processes$.subscribe((p) => {
        let classesIcon = {
            [_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ProcessMessageKind.Scheduled]: "fas fa-clock px-2",
            [_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ProcessMessageKind.Started]: "fas fa-cog fa-spin px-2",
            [_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ProcessMessageKind.Succeeded]: "fas fa-check fv-text-success px-2",
            [_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ProcessMessageKind.Failed]: "fas fa-times fv-text-error px-2",
            [_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ProcessMessageKind.Log]: "fas fa-cog fa-spin px-2",
        };
        let doneMessages = [_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ProcessMessageKind.Succeeded, _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.ProcessMessageKind.Failed];
        let actions = p.context
            ? [{
                    name: 'report',
                    exe: () => _builder_editor_views_context_view__WEBPACK_IMPORTED_MODULE_3__.ContextView.reportContext(p.context)
                }]
            : [];
        Notifier.notify({
            title: p.title,
            message: (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__.attr$)(p.messages$, (step) => step.text),
            classIcon: (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__.attr$)(p.messages$, (step) => classesIcon[step.kind]),
            actions,
            timeout: p.messages$.pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.filter)(m => doneMessages.includes(m.kind)), (0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.take)(1), (0,rxjs_operators__WEBPACK_IMPORTED_MODULE_2__.delay)(1000))
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
    constructor(appStore) {
        this.appStore = appStore;
    }
    /**
     * Popup a notification with level=='Info'
     *
     * @param message content
     * @param title title
     * @param actions available actions
     */
    static notify({ message, title, classIcon, actions, timeout }) {
        Notifier.popup({ message, title, actions, classIcon, timeout, classBorder: "" });
    }
    /**
     * Popup a notification with level=='Error'
     *
     * @param message content
     * @param title title
     * @param actions available actions
     */
    static error({ message, title, actions }) {
        Notifier.popup({ message, title, actions, classIcon: Notifier.classesIcon[4], classBorder: Notifier.classesBorder[4] });
    }
    /**
     * Popup a notification with level=='Warning'
     *
     * @param message content
     * @param title title
     * @param actions available actions
     */
    static warning({ message, title, actions }) {
        Notifier.popup({ message, title, actions, classIcon: Notifier.classesIcon[3], classBorder: Notifier.classesBorder[3] });
    }
    static popup({ message, title, actions, classIcon, classBorder, timeout }) {
        let view = {
            class: "m-2 p-2 my-1 bg-white rounded " + classBorder,
            style: { border: 'solid' },
            children: [
                {
                    class: "fas fa-times",
                    style: { float: 'right', cursor: 'pointer' },
                    onclick: (event) => {
                        event.target.parentElement.remove();
                    }
                },
                {
                    class: 'd-flex py-2 align-items-center',
                    children: [
                        { tag: 'i', class: classIcon },
                        { tag: 'span', class: 'd-block', innerText: title }
                    ]
                },
                message ? { tag: 'span', class: 'd-block px-2', innerText: message } : {},
                {
                    class: 'd-flex align-space-around mt-2 fv-pointer',
                    children: actions.map(action => ({
                        tag: 'span',
                        class: "mx-2 p-2 fv-bg-background-alt rounded fv-hover-bg-background fv-hover-text-focus fv-text-primary",
                        innerText: action.name,
                        onclick: () => action.exe()
                    }))
                }
            ],
            connectedCallback: (elem) => {
                timeout && timeout.subscribe(() => elem.remove());
            }
        };
        let div = (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_1__.render)(view);
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


/***/ }),

/***/ "./on-load.ts":
/*!********************!*\
  !*** ./on-load.ts ***!
  \********************/
/***/ ((module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.a(module, async (__webpack_handle_async_dependencies__) => {
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "initializeRessources": () => (/* binding */ initializeRessources),
/* harmony export */   "connectStreams": () => (/* binding */ connectStreams),
/* harmony export */   "initDrawingArea": () => (/* binding */ initDrawingArea)
/* harmony export */ });
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! rxjs */ "rxjs");
/* harmony import */ var rxjs__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(rxjs__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! rxjs/operators */ "rxjs/operators");
/* harmony import */ var rxjs_operators__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(rxjs_operators__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! @youwol/flux-svg-plots */ "@youwol/flux-svg-plots");
/* harmony import */ var _youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3__);
/* harmony import */ var _youwol_fv_context_menu__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! @youwol/fv-context-menu */ "@youwol/fv-context-menu");
/* harmony import */ var _youwol_fv_context_menu__WEBPACK_IMPORTED_MODULE_4___default = /*#__PURE__*/__webpack_require__.n(_youwol_fv_context_menu__WEBPACK_IMPORTED_MODULE_4__);
/* harmony import */ var _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! ./builder-editor/builder-state/index */ "./builder-editor/builder-state/index.ts");
/* harmony import */ var _builder_editor_builder_plots_index__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! ./builder-editor/builder-plots/index */ "./builder-editor/builder-plots/index.ts");
/* harmony import */ var _builder_editor_index__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! ./builder-editor/index */ "./builder-editor/index.ts");
/* harmony import */ var _layout_editor_index__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(/*! ./layout-editor/index */ "./layout-editor/index.ts");
/* harmony import */ var _notification__WEBPACK_IMPORTED_MODULE_9__ = __webpack_require__(/*! ./notification */ "./notification.ts");
/* harmony import */ var _clients_assets_browser_client__WEBPACK_IMPORTED_MODULE_10__ = __webpack_require__(/*! ./clients/assets-browser.client */ "./clients/assets-browser.client.ts");
/* harmony import */ var _builder_editor_views_assets_explorer_view__WEBPACK_IMPORTED_MODULE_11__ = __webpack_require__(/*! ./builder-editor/views/assets-explorer.view */ "./builder-editor/views/assets-explorer.view.ts");
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_12__ = __webpack_require__(/*! @youwol/flux-view */ "@youwol/flux-view");
/* harmony import */ var _youwol_flux_view__WEBPACK_IMPORTED_MODULE_12___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_view__WEBPACK_IMPORTED_MODULE_12__);
/* harmony import */ var _loading_views__WEBPACK_IMPORTED_MODULE_13__ = __webpack_require__(/*! ./loading.views */ "./loading.views.ts");














let { appStore, appObservables, layoutEditor } = await initializeRessources();
let workflowPlotter = initDrawingArea(appStore, appObservables);
(0,_notification__WEBPACK_IMPORTED_MODULE_9__.plugNotifications)(appStore, workflowPlotter);
let contextState = new _builder_editor_index__WEBPACK_IMPORTED_MODULE_7__.ContextMenuState(appStore, workflowPlotter.drawingArea);
new _youwol_fv_context_menu__WEBPACK_IMPORTED_MODULE_4__.ContextMenu.View({ state: contextState, class: "fv-bg-background" });
connectStreams(appStore, workflowPlotter, layoutEditor, appObservables);
let projectId = new URLSearchParams(window.location.search).get("id");
let uri = new URLSearchParams(window.location.search).get("uri");
if (projectId) {
    let loadingDiv = document.getElementById("content-loading-screen");
    let divProjectLoading = (0,_loading_views__WEBPACK_IMPORTED_MODULE_13__.loadingProjectView)(loadingDiv);
    appStore.environment.getProject(projectId).subscribe((project) => {
        divProjectLoading.innerText = `> project loaded`;
        divProjectLoading.style.setProperty("color", "green");
        appStore.loadProject(projectId, project, (event) => {
            (0,_loading_views__WEBPACK_IMPORTED_MODULE_13__.loadingLibView)(event, loadingDiv);
        });
    });
}
else if (uri) {
    appStore.loadProjectURI(encodeURI(uri));
}
async function initializeRessources() {
    let defaultLog = false;
    let appObservables = _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_5__.AppObservables.getInstance();
    let debugSingleton = _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_5__.AppDebugEnvironment.getInstance();
    debugSingleton.workflowUIEnabled = defaultLog;
    debugSingleton.observableEnabled = defaultLog;
    debugSingleton.workflowUIEnabled = defaultLog;
    debugSingleton.workflowViewEnabled = defaultLog;
    debugSingleton.WorkflowBuilderEnabled = defaultLog;
    debugSingleton.renderTopicEnabled = defaultLog;
    debugSingleton.workflowView$Enabled = defaultLog;
    let layoutEditor = await (0,_layout_editor_index__WEBPACK_IMPORTED_MODULE_8__.createLayoutEditor)();
    let doc = layoutEditor.Canvas.getDocument();
    let environment = new _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Environment({ console: undefined,
        renderingWindow: doc.defaultView,
        executingWindow: window
    });
    debugSingleton.logWorkflowBuilder({
        level: _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_5__.LogLevel.Info,
        message: "Environment",
        object: { environment }
    });
    let appStore = _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_5__.AppStore.getInstance(environment);
    _clients_assets_browser_client__WEBPACK_IMPORTED_MODULE_10__.AssetsBrowserClient.appStore = appStore;
    // A single instance of assets browser to keep in memory expandeds nodes etc
    _builder_editor_views_assets_explorer_view__WEBPACK_IMPORTED_MODULE_11__.AssetsExplorerView.singletonState = new _builder_editor_views_assets_explorer_view__WEBPACK_IMPORTED_MODULE_11__.AssetsExplorerView.State({
        appStore
    });
    _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Journal.registerView({
        name: "ConfigurationStatus",
        isCompatible: (data) => data instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.ConfigurationStatus,
        view: (data) => (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_12__.render)(_builder_editor_index__WEBPACK_IMPORTED_MODULE_7__.ConfigurationStatusView.journalWidget(data))
    });
    _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.Journal.registerView({
        name: "ExpectationStatus",
        isCompatible: (data) => data instanceof _youwol_flux_core__WEBPACK_IMPORTED_MODULE_2__.ExpectationStatus,
        view: (data) => (0,_youwol_flux_view__WEBPACK_IMPORTED_MODULE_12__.render)(_builder_editor_index__WEBPACK_IMPORTED_MODULE_7__.ExpectationView.journalWidget(data))
    });
    return {
        appStore,
        appObservables,
        layoutEditor
    };
}
function setUiState(state) {
    let renderNode = document.getElementById("render-component");
    let builderNode = document.getElementById("builder-component");
    builderNode.classList.remove("combined", "builder", "render", "none");
    renderNode.classList.remove("combined", "builder", "render", "none");
    builderNode.classList.add(state.mode);
    renderNode.classList.add(state.mode);
}
function connectStreams(appStore, workflowPlotter, layoutEditor, appObservables) {
    let loading = true;
    appObservables.packagesLoaded$.subscribe(() => document.getElementById("loading-screen").remove());
    appObservables.uiStateUpdated$.subscribe((state) => setUiState(state));
    appObservables.adaptorEdited$.subscribe(({ adaptor, connection }) => { });
    let layoutEditor$ = new rxjs__WEBPACK_IMPORTED_MODULE_0__.ReplaySubject(1);
    appObservables.renderingLoaded$.subscribe((d) => {
        (0,_layout_editor_index__WEBPACK_IMPORTED_MODULE_8__.initLayoutEditor)(layoutEditor, d, appStore);
        layoutEditor$.next(layoutEditor);
    });
    (0,rxjs__WEBPACK_IMPORTED_MODULE_0__.combineLatest)([layoutEditor$, appObservables.modulesUpdated$])
        .subscribe(([editor, diff]) => {
        let notReplaced = diff.removedElements.filter(mdle => !diff.createdElements.map(m => m.moduleId).includes(mdle.moduleId));
        (0,_layout_editor_index__WEBPACK_IMPORTED_MODULE_8__.removeTemplateElements)(notReplaced, editor);
        if (loading)
            (0,_layout_editor_index__WEBPACK_IMPORTED_MODULE_8__.replaceTemplateElements)(diff.createdElements.map((m) => m.moduleId), editor, appStore);
        if (!loading)
            (0,_layout_editor_index__WEBPACK_IMPORTED_MODULE_8__.autoAddElementInLayout)(diff, editor, appStore);
        (0,_layout_editor_index__WEBPACK_IMPORTED_MODULE_8__.setDynamicComponentsBlocks)(appStore, editor);
    });
    (0,rxjs__WEBPACK_IMPORTED_MODULE_0__.combineLatest)([layoutEditor$, appObservables.activeLayerUpdated$])
        .subscribe(([editor, diff]) => {
        (0,_layout_editor_index__WEBPACK_IMPORTED_MODULE_8__.setDynamicComponentsBlocks)(appStore, editor);
    });
    (0,rxjs__WEBPACK_IMPORTED_MODULE_0__.combineLatest)([layoutEditor$, appObservables.uiStateUpdated$]).pipe((0,rxjs_operators__WEBPACK_IMPORTED_MODULE_1__.filter)(([editor, state]) => state.mode === "combined" || state.mode === "render")).subscribe(([editor, state]) => (0,_layout_editor_index__WEBPACK_IMPORTED_MODULE_8__.replaceTemplateElements)(appStore.project.workflow.modules.map(m => m.moduleId), editor, appStore));
    (0,rxjs__WEBPACK_IMPORTED_MODULE_0__.combineLatest)([layoutEditor$, appObservables.unselect$])
        .subscribe(([editor, _]) => {
        editor.Commands.stop("show-attributes");
    });
    let selection$ = (0,rxjs__WEBPACK_IMPORTED_MODULE_0__.merge)(appObservables.moduleSelected$, appObservables.connectionSelected$);
    (0,rxjs__WEBPACK_IMPORTED_MODULE_0__.combineLatest)([layoutEditor$, selection$]).subscribe(([editor, _]) => {
        editor.Commands.run("show-attributes");
    });
    (0,rxjs__WEBPACK_IMPORTED_MODULE_0__.combineLatest)([layoutEditor$, appObservables.uiStateUpdated$])
        .subscribe(([editor, _]) => {
        editor.refresh();
    });
    appObservables.ready$.subscribe(() => {
        document.getElementById("attributes-panel").appendChild((0,_builder_editor_index__WEBPACK_IMPORTED_MODULE_7__.createAttributesPanel)(appStore, appObservables));
    });
    layoutEditor$.subscribe(r => {
        loading = false;
    });
}
function initDrawingArea(appStore, appObservables) {
    let plottersObservables = _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_5__.AppBuildViewObservables.getInstance();
    let width = 1000;
    let height = 1000;
    let drawingArea = (0,_youwol_flux_svg_plots__WEBPACK_IMPORTED_MODULE_3__.createDrawingArea)({
        containerDivId: "wf-builder-view",
        width: width,
        height: height,
        xmin: -width / 2.,
        ymin: -width / 2.,
        xmax: width / 2.,
        ymax: width / 2.,
        margin: 50,
        overflowDisplay: { left: 1e8, right: 1e8, top: 1e8, bottom: 1e8 }
    });
    return new _builder_editor_builder_plots_index__WEBPACK_IMPORTED_MODULE_6__.WorkflowPlotter(drawingArea, appObservables, plottersObservables, appStore);
}

__webpack_handle_async_dependencies__();
}, 1);

/***/ }),

/***/ "./top-banner/commands.ts":
/*!********************************!*\
  !*** ./top-banner/commands.ts ***!
  \********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "commandsGeneral": () => (/* binding */ commandsGeneral)
/* harmony export */ });
/* harmony import */ var _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../builder-editor/builder-state/index */ "./builder-editor/builder-state/index.ts");
/* harmony import */ var _layer_picker_view__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./layer-picker.view */ "./top-banner/layer-picker.view.ts");


function commandsGeneral(appStore, editor) {
    let debugSingleton = _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.AppDebugEnvironment.getInstance();
    let cmds = [
        ['toggle-render-view', {
                run(editor, sender) {
                    if (appStore.uiState.mode == "builder")
                        appStore.setUiState(new _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.UiState("combined", false, false));
                    if (appStore.uiState.mode == "none")
                        appStore.setUiState(new _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.UiState("render", false, false));
                },
                stop(editor, sender) {
                    if (appStore.uiState.mode == "combined")
                        appStore.setUiState(new _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.UiState("builder", false, false));
                    if (appStore.uiState.mode == "render")
                        appStore.setUiState(new _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.UiState("none", false, false));
                }
            }],
        ['toggle-builder-view', {
                run(editor, sender) {
                    if (appStore.uiState.mode == "render")
                        appStore.setUiState(new _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.UiState("combined", false, false));
                    if (appStore.uiState.mode == "none")
                        appStore.setUiState(new _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.UiState("builder", false, false));
                },
                stop(editor, sender) {
                    if (appStore.uiState.mode == "combined")
                        appStore.setUiState(new _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.UiState("render", false, false));
                    if (appStore.uiState.mode == "builder")
                        appStore.setUiState(new _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.UiState("none", false, false));
                }
            }],
        ['toggle-fullscreen', {
                run(editor, sender) {
                    // see  document.addEventListener("fullscreenchange"...) callback
                    document.documentElement.requestFullscreen();
                },
            }],
        ['duplicate-module', {
                run(editor, sender) {
                    let mdles = appStore.getModulesSelected();
                    appStore.duplicateModules(mdles);
                }
            }],
        ['horizontal-align', {
                run(editor, sender) {
                    let mdles = appStore.getModulesSelected();
                    appStore.alignH(mdles);
                }
            }],
        ['vertical-align', {
                run(editor, sender) {
                    let mdles = appStore.getModulesSelected();
                    appStore.alignV(mdles);
                }
            }],
        ['group-module', {
                run(editor, sender) {
                    appStore.addGroup(appStore.getModulesSelected().map(m => m.moduleId));
                }
            }],
        ['group-as-component', {
                run(editor, sender) {
                    appStore.addComponent(appStore.getModulesSelected().map(m => m.moduleId));
                }
            }],
        ['publish-component', {
                run(editor, sender) {
                    appStore.publishComponent(appStore.getModuleSelected());
                }
            }],
        ['display-tree-structure', {
                run(editor, sender) {
                    const div = (0,_layer_picker_view__WEBPACK_IMPORTED_MODULE_1__.createLayerPickerView)(appStore, editor);
                    document.getElementById("panel__app-tree-structure").innerHTML = "";
                    document.getElementById("panel__app-tree-structure").appendChild(div);
                }
            }
        ]
    ];
    document.addEventListener("fullscreenchange", () => {
        document.querySelectorAll(".controls-panel").forEach(control => control.classList.toggle("fullscreen"));
        editor.refresh();
    });
    debugSingleton.debugOn &&
        debugSingleton.logRenderTopic({ level: _builder_editor_builder_state_index__WEBPACK_IMPORTED_MODULE_0__.LogLevel.Info, message: "General commands", object: { cmds } });
    return cmds;
}


/***/ }),

/***/ "./top-banner/layer-picker.view.ts":
/*!*****************************************!*\
  !*** ./top-banner/layer-picker.view.ts ***!
  \*****************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "createLayerPickerView": () => (/* binding */ createLayerPickerView)
/* harmony export */ });
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @youwol/flux-core */ "@youwol/flux-core");
/* harmony import */ var _youwol_flux_core__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__);

function createLayerPickerView(appStore, editor) {
    let subscriptions = [];
    function createContentRecursive(layer) {
        // const childrenModules = layer.moduleIds.map(moduleId => ({ tag: 'div', class: "text-muted  px-1", innerText: appStore.getModule(moduleId).configuration.title }))
        const childrenLayers = layer.children.map(child => createContentRecursive(child));
        const selectedClass = layer.layerId == appStore.getActiveLayer().layerId ? "font-weight-bold" : "";
        return {
            class: "w-100",
            __label: {
                innerText: layer.title,
                class: "flux-hoverable w-100 px-1 " + selectedClass,
                onclick: () => appStore.selectActiveLayer(layer.layerId)
            },
            __div: {
                class: "children pl-2 w-100",
                children: childrenLayers
            }
        };
    }
    let view = (0,_youwol_flux_core__WEBPACK_IMPORTED_MODULE_0__.createHTMLElement)({
        data: {
            id: "tree-view-layers",
            class: "px-2 text-light border text-left flux-bg-primary",
            onmouseout: (event) => {
                if (event.path[0].id == "tree-view-layers") {
                    const selection = document.getElementById("tree-view-layers").querySelector(".children");
                    selection && selection.remove();
                }
            },
            onclick: () => {
                editor.Commands.run("display-tree-structure");
            },
            __div: {
                class: "",
                innerHTML: "active layer <i class='fas fa-caret-down pl-2'></i>",
                children: [{
                        tag: 'div',
                        class: 'flux-bg-primary text-black  children small py-2',
                        __div: createContentRecursive(appStore.project.workflow.rootLayerTree)
                    }]
            },
        },
        subscriptions,
        classesDict: {}
    });
    return view;
}


/***/ }),

/***/ "./top-banner/panels.ts":
/*!******************************!*\
  !*** ./top-banner/panels.ts ***!
  \******************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "getGeneralPanels": () => (/* binding */ getGeneralPanels)
/* harmony export */ });
/* harmony import */ var _builder_editor_views_share_uri_view__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../builder-editor/views/share-uri.view */ "./builder-editor/views/share-uri.view.ts");

function getGeneralPanels(appStore) {
    return [{
            id: 'app-basic-actions',
            el: '#panel__app-basic-actions',
            buttons: [
                {
                    id: 'save-project',
                    className: 'btn-save-project',
                    label: '<i class="fas fa-save panel-action" data-toggle="tooltip" title="Save project" ></i>',
                    command(editor) { appStore.saveProject(); }
                },
                {
                    id: 'share-uri',
                    className: 'btn-share-uri',
                    label: '<i class="fas fa-link panel-action" data-toggle="tooltip" title="share uri" ></i>',
                    command(editor) { _builder_editor_views_share_uri_view__WEBPACK_IMPORTED_MODULE_0__.ShareUriView.popupModal(appStore); }
                },
                {
                    id: 'undo',
                    className: 'btn-undo',
                    label: '<i class="fas fa-undo panel-action" data-toggle="tooltip" title="Undo" ></i>',
                    command(editor) { appStore.undo(); }
                },
                {
                    id: 'redo',
                    className: 'btn-redo',
                    label: '<i class="fas fa-redo panel-action" data-toggle="tooltip" title="Redo" ></i>',
                    command(editor) { appStore.redo(); }
                },
                {
                    id: 'settings',
                    className: 'btn-settings',
                    label: '<i class="fas fa-cog panel-action" data-toggle="tooltip" title="open settings panel" ></i>',
                    command(editor) { appStore.projectSettings(); }
                }
            ],
        }, {
            id: 'app-layout-builder-actions',
            el: '#panel__app-layout-builder-actions',
            buttons: [
                {
                    id: 'toggle-builder-view',
                    active: true,
                    className: 'app-layout-builder-actions',
                    label: '<i id="toggle-builder-view" class="fas fa-project-diagram  panel-action" data-toggle="tooltip" title="Toggle builder view"></i>',
                    command: 'toggle-builder-view'
                }
            ]
        },
        {
            id: 'app-layout-render-actions',
            el: '#panel__app-layout-render-actions',
            buttons: [
                {
                    id: 'toggle-render-view',
                    className: 'app-layout-render-actions',
                    label: '<i id="toggle-render-view" class="fas fa-eye  panel-action" data-toggle="tooltip" title="Toggle builder view"></i>',
                    command: 'toggle-render-view'
                },
            ],
        },
        {
            id: 'app-layout-actions',
            el: '#panel__app-layout-actions',
            buttons: [
                {
                    id: 'toggle-full-screen',
                    active: false,
                    className: 'app-layout-actions',
                    label: '<i id="toggle-render-view" class="fas fa-expand  panel-action" data-toggle="tooltip" title="Fullscreen mode"></i>',
                    command: 'toggle-fullscreen',
                    toggable: false
                },
            ],
        },
        {
            id: 'panel__app-selection-actions',
            el: '#panel__app-selection-actions',
            buttons: [
                {
                    id: 'duplicate-module',
                    active: false,
                    className: 'selection-actions',
                    label: '<i id="toggle-render-view" class="fas fa-clone panel-action" data-toggle="tooltip" title="duplicate selected modules"></i>',
                    command: 'duplicate-module',
                    toggable: false
                },
                {
                    id: 'horizontal-align',
                    active: false,
                    className: 'selection-actions',
                    label: '<i id="toggle-render-view" class="fas fa-ruler-vertical panel-action" data-toggle="tooltip" title="horizontal align selected modules"></i>',
                    command: 'horizontal-align',
                    toggable: false
                },
                {
                    id: 'vertical-align',
                    active: false,
                    className: 'selection-actions',
                    label: '<i id="toggle-render-view" class="fas fa-ruler-horizontal panel-action" data-toggle="tooltip" title="vertical align selected modules"></i>',
                    command: 'vertical-align',
                    toggable: false
                },
                {
                    id: 'group-module',
                    active: false,
                    className: 'selection-actions',
                    label: '<i id="toggle-render-view" class="fas fa-object-group panel-action" data-toggle="tooltip" title="group selected modules"></i>',
                    command: 'group-module',
                    toggable: false
                }
            ],
        }, {
            id: 'panel__app-component-actions',
            el: '#panel__app-component-actions',
            buttons: [
                {
                    id: 'create-component',
                    active: false,
                    className: 'selection-actions',
                    label: '<i id="create-component" class="fas fa-cube panel-action" data-toggle="tooltip" title="create a component from selected modules"></i>',
                    command: 'group-as-component',
                    toggable: false
                },
                {
                    id: 'publish-component',
                    active: false,
                    className: 'selection-actions',
                    label: '<i id="publish-component" class="fas fa-upload panel-action" data-toggle="tooltip" title="publish selected component"></i>',
                    command: 'publish-component',
                    toggable: false
                }
            ]
        },
        {
            id: 'panel__app-tree-structure',
            el: '#panel__app-tree-structure',
            buttons: [
                {
                    id: 'display-tree-structure',
                    active: false,
                    className: 'tree-structure',
                    label: '<label class="text-light border px-2" >active layer <i class="fas fa-caret-down pl-2"></i> </label>',
                    command: 'display-tree-structure',
                    toggable: false
                }
            ]
        }];
}


/***/ })

}]);
//# sourceMappingURL=on-load_ts.57b6ab86e5de51022e65.js.map