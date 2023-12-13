class State {
  constructor({ triggerRun, project, flowId, stepId, rxjs, projectsRouter }) {
    this.triggerRun = triggerRun;
    this.projectsRouter = projectsRouter;
    this.project = project;
    this.stepId = stepId;
    this.flowId = flowId;
    const inputs$ = projectsRouter.executeStepGetCommand$({
      commandId: "get_input_data",
      projectId: project.id,
      flowId,
      stepId,
    });
    this.dependencies$ = inputs$.pipe(
      rxjs.operators.map((data) => Object.keys(data)),
    );
    const config$ = projectsRouter.getStepConfiguration$({
      projectId: project.id,
      flowId,
      stepId,
    });
    config$.subscribe((config) => {
      const synchronizedDependencies = config.synchronizedDependencies || [];
      this.selectedPackages$.next(synchronizedDependencies);
    });
    this.selectedPackages$ = new rxjs.BehaviorSubject([]);
  }

  togglePackage(name) {
    const selected = this.selectedPackages$.getValue();
    const base = selected.filter((n) => n !== name);
    if (selected.indexOf(name) > -1) {
      this.selectedPackages$.next(base);
      return;
    }
    this.selectedPackages$.next([...base, name]);
  }

  run() {
    this.triggerRun({
      configuration: { synchronizedDependencies: this.selectedPackages$.value },
    });
  }
}

class SyncDependenciesView {
  tag = "div";
  class =
    "h-100 w-100 rounded fv-bg-background-alt yw-animate-in yw-box-shadow p-3";

  constructor({ state }) {
    this.children = [
      {
        tag: "h1",
        class: "w-100 text-center",
        innerText: "Dependencies Step",
      },
      {
        tag: "div",
        innerText:
          "Check the dependencies you want to synchronized from the projects",
      },
      {
        tag: "ul",
        children: {
          policy: "replace",
          source$: state.dependencies$,
          vdomMap: (dependencies) => {
            return dependencies.map((name) => {
              return {
                tag: "li",
                class: "d-flex align-items-center",
                children: [
                  {
                    tag: "input",
                    type: "checkbox",
                    onclick: () => state.togglePackage(name),
                    checked: {
                      source$: state.selectedPackages$,
                      vdomMap: (packages) => packages.indexOf(name) > -1,
                    },
                  },
                  {
                    tag: "span",
                    innerText: `${name}`,
                  },
                ],
              };
            });
          },
        },
      },
      {
        tag: "div",
        class:
          "fv-bg-secondary rounded p-2 border fv-hover-xx-lighter fv-pointer",
        style: {
          width: "fit-content",
        },
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

  const vDom = new SyncDependenciesView({
    state,
  });

  return rxVdom.render(vDom);
}

// noinspection JSAnnotator
return getView;
