class State {
  constructor({ modalState, project, flowId, stepId, rxjs, projectsRouter }) {
    this.modalState = modalState;
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
      rxjs.operators.map((data) => Object.keys(data))
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

  updateConfiguration() {
    this.selectedPackages$
      .pipe(
        rxjs.operators.mergeMap((packages) => {
          return this.projectsRouter.updateStepConfiguration$({
            projectId: this.project.id,
            flowId: this.flowId,
            stepId: this.stepId,
            body: { synchronizedDependencies: packages },
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
        innerText: "Dependencies Step",
      },
      {
        innerText:
          "Check the dependencies you want to synchronized from the projects",
      },
      {
        tag: "ul",
        children: fluxView.children$(state.dependencies$, (dependencies) => {
          return dependencies.map((name) => {
            return {
              tag: "li",
              class: "d-flex align-items-center",
              children: [
                {
                  tag: "input",
                  type: "checkbox",
                  onclick: () => state.togglePackage(name),
                  checked: fluxView.attr$(
                    state.selectedPackages$,
                    (packages) => packages.indexOf(name) > -1
                  ),
                },
                {
                  tag: "span",
                  innerText: name,
                },
              ],
            };
          });
        }),
      },
      {
        class:
          "fv-bg-secondary rounded p-2 border fv-hover-xx-lighter fv-pointer",
        style: { width: "fit-content" },
        innerText: "Apply & run",
        onclick: () => {
          state.updateConfiguration();
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
