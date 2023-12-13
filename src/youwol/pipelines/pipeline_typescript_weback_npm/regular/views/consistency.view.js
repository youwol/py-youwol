class State {
  constructor({ triggerRun, project, flowId, stepId, rxjs, projectsRouter }) {
    this.triggerRun = triggerRun;
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
        }),
      )
      .subscribe();
  }

  run() {
    this.triggerRun({
      configuration: { synchronizedDependencies: this.selectedPackages$.value },
    });
  }
}

class ConsistencyView {
  tag = "div";
  class = "h-100 w-100 rounded fv-bg-background-alt border p-3";

  constructor({ state }) {
    this.children = [
      {
        tag: "h1",
        class: "w-100 text-center",
        innerText: "Consistency Step",
      },
      {
        tag: "div",
        innerText: "Provide the path of the test configuration:",
      },
      {
        tag: "input",
        type: "text",
        placeholder: "path of the config file",
        value: { source$: state.configPath$, vdomMap: (p) => p },

        onchange: (ev) => {
          state.configPath$.next(ev.target.value);
        },
      },
      {
        tag: "div",
        innerText: "Provide the number of run:",
      },
      {
        tag: "input",
        type: "number",
        value: { source$: state.count$, vdomMap: (p) => p },
        onchange: (ev) => {
          state.count$.next(parseInt(ev.target.value));
        },
      },
      {
        tag: "div",
        class: "my-3",
      },
      {
        tag: "div",
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

async function getView({
  triggerRun,
  project,
  flowId,
  stepId,
  projectsRouter,
  webpmClient,
}) {
  const { rxjs, rxVdom } = await webpmClient.install({
    modules: ["@youwol/rx-vdom#^1.0.1 as rxVdom", "rxjs#^7.5.6 as rxjs"],
  });
  const state = new State({
    triggerRun,
    project,
    flowId,
    stepId,
    rxjs,
    projectsRouter,
  });

  const vDom = new ConsistencyView({
    state,
  });

  return rxVdom.render(vDom);
}

// noinspection JSAnnotator
return getView;
