class State {
  constructor({ modalState, project, flowId, stepId, rxjs, projectsRouter }) {
    this.modalState = modalState;
    this.projectsRouter = projectsRouter;
    this.project = project;
    this.stepId = stepId;
    this.flowId = flowId;

    const config$ = projectsRouter.getStepConfiguration$({
      projectId: project.id,
      flowId,
      stepId,
    });
    this.count$ = new rxjs.Subject();
    this.configPath$ = new rxjs.Subject();
    config$.subscribe((config) => {
      this.count$.next(config.count || 10);
      this.configPath$.next(config.configPath || "");
    });
    rxjs
      .combineLatest([this.count$, this.configPath$])
      .pipe(
        rxjs.operators.skip(1),
        rxjs.operators.mergeMap(([count, configPath]) => {
          return this.projectsRouter.updateStepConfiguration$({
            projectId: this.project.id,
            flowId: this.flowId,
            stepId: this.stepId,
            body: { count, configPath },
          });
        })
      )
      .subscribe();
  }

  run() {
    const d = {
      projectId: this.project.id,
      flowId: this.flowId,
      stepId: this.stepId,
    };
    rxjs
      .combineLatest([
        this.projectsRouter.getPipelineStepStatus$(d),
        this.projectsRouter.runStep$(d),
      ])
      .pipe(rxjs.operators.take(1))
      .subscribe();
    this.modalState.ok$.next(true);
  }
}

class SyncDependenciesView {
  class = "h-100 w-100 rounded fv-bg-background-alt border p-3";
  constructor({ state, fluxView }) {
    this.children = [
      {
        tag: "h1",
        class: "w-100 text-center",
        innerText: "Consistency Step",
      },
      {
        innerText: "Provide the path of the test configuration:",
      },
      {
        tag: "input",
        type: "text",
        placeholder: "path of the config file",
        value: fluxView.attr$(state.configPath$, (p) => p),
        onchange: (ev) => {
          state.configPath$.next(ev.target.value);
        },
      },
      {
        innerText: "Provide the number of run:",
      },
      {
        tag: "input",
        type: "number",
        value: fluxView.attr$(state.count$, (p) => p),
        onchange: (ev) => {
          state.count$.next(parseInt(ev.target.value));
        },
      },
      { class: "my-3" },
      {
        class:
          "fv-bg-secondary rounded p-2 border fv-hover-xx-lighter fv-pointer",
        style: { width: "fit-content" },
        innerText: "Apply & run",
        onclick: () => {
          state.run();
        },
      },
    ];
  }
}
function getView({
  modalState,
  project,
  flowId,
  stepId,
  fluxView,
  rxjs,
  projectsRouter,
}) {
  const state = new State({
    modalState,
    project,
    flowId,
    stepId,
    rxjs,
    projectsRouter,
  });

  return new SyncDependenciesView({
    state,
    fluxView,
    rxjs,
  });
}

// noinspection JSAnnotator
return getView;
