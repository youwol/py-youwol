const webpm = window["webpm"];

const { RxDom, RxJs, HttpClients } = await webpm.install({
  modules: [
    "@youwol/rx-vdom#^1.0.3 as RxDom",
    "rxjs#^7.5.6 as RxJs",
    "@youwol/http-clients#^3.0.1 as HttpClients",
  ],
  css: [
    "bootstrap#^5.3.3~bootstrap.min.css",
    "fontawesome#5.12.1~css/all.min.css",
  ],
  displayLoadingScreen: true,
});

const { CdnSessionsStorage } = HttpClients;
const { BehaviorSubject, combineLatest, map, mergeMap, skip } = RxJs;

const classes = {
  chevron: "fas fa-chevron-down p-2 fa-2x text-secondary",
  itemViewContainer:
      "d-flex align-items-center justify-content-between item-view",
  itemCheckContainer:
      "border rounded-circle m-2 d-flex flex-column justify-content-center item-check-container",
  itemDelete: "delete fas fa-times text-danger float-right px-3",
  itemSuccess: "fas fa-check mx-auto text-success",
  footer: "d-flex align-items-center px-3 border-top py-2 text-secondary",
};

const Filter = {
  ALL: 1,
  ACTIVE: 2,
  COMPLETED: 3,
};

class AppState {
  static STORAGE_KEY = "todo-list";
  client = new CdnSessionsStorage.Client();
  constructor() {
    this.items$ = new BehaviorSubject([]);

    this.client
        .getData$({
          packageName: "{{application_name}}",
          dataName: AppState.STORAGE_KEY,
        })
        .subscribe((d) => {
          this.items$.next(d.items ? d.items : []);
        });
    this.items$
        .pipe(
            skip(1),
            mergeMap((items) =>
                this.client.postData$({
                  packageName: "{{application_name}}",
                  dataName: AppState.STORAGE_KEY,
                  body: { items },
                }),
            ),
        )
        .subscribe(() => {
          console.log("data saved");
        });

    this.completed$ = this.items$.pipe(
        map((items) => items.reduce((acc, item) => acc && item.done, true)),
    );
    this.remaining$ = this.items$.pipe(
        map((items) => items.filter((item) => !item.done)),
    );
    this.filterMode$ = new BehaviorSubject(Filter.ALL);
    this.filterFcts = {
      [Filter.ALL]: () => true,
      [Filter.ACTIVE]: (item) => !item.done,
      [Filter.COMPLETED]: (item) => item.done,
    };
    this.selectedItems$ = combineLatest([this.items$, this.filterMode$]).pipe(
        map(([items, mode]) =>
            items.filter((item) => this.filterFcts[mode](item)),
        ),
    );
  }

  toggleAll() {
    const completed = this.getItems().reduce(
        (acc, item) => acc && item.done,
        true,
    );
    this.items$.next(
        this.getItems().map((item) => ({
          id: item.id,
          name: item.name,
          done: !completed,
        })),
    );
  }

  addItem(name) {
    const item = { id: Date.now(), name, completed: false };
    this.items$.next([...this.getItems(), item]);
    return item;
  }

  deleteItem(id) {
    this.items$.next(this.getItems().filter((item) => item.id !== id));
  }

  toggleItem(id) {
    const items = this.getItems().map((item) =>
        item.id === id
            ? { id: item.id, name: item.name, done: !item.done }
            : item,
    );
    this.items$.next(items);
  }

  setName(id, name) {
    const items = this.getItems().map((item) =>
        item.id === id ? { id: item.id, name, done: item.done } : item,
    );
    this.items$.next(items);
  }

  getItems() {
    return this.items$.getValue();
  }

  setFilter(mode) {
    this.filterMode$.next(mode);
  }
}

class HeaderView {
  tag = "header";
  class = "header";

  constructor(appState) {
    this.children = [
      {
        tag: "h1",
        innerText: "todos",
      },
      {
        tag: "div",
        class: "d-flex align-items-center",
        children: [
          {
            tag: "i",
            class: {
              source$: appState.completed$,
              vdomMap: (completed) => (completed ? "text-dark" : "text-light"),
              wrapper: (d) => `${d} ${classes.chevron}`,
            },
            onclick: () => appState.toggleAll(),
          },
          {
            tag: "input",
            autofocus: "autofocus",
            autocomplete: "off",
            placeholder: "What needs to be done?",
            class: "new-todo",
            onkeypress: (ev) => {
              ev.key === "Enter" &&
              appState.addItem(ev.target.value) &&
              (ev.target.value = "");
            },
          },
        ],
      },
    ];
  }
}

class ItemEditionView {
  tag = "input";
  type = "text";
  onclick = (ev) => ev.stopPropagation();
  onkeypress = (ev) => {
    if (ev.key === "Enter") {
      // otherwise the onblur event is triggered while the element does not exist anymore
      ev.target.onblur = () => {};
      this.appState.setName(this.item.id, ev.target.value);
    }
  };
  onblur = (ev) => this.appState.setName(this.item.id, ev.target.value);

  constructor(item, appState) {
    Object.assign(this, { item, appState });
  }
}

class ItemPresentationView {
  tag = "span";
  ondblclick = () => this.edited$.next(true);

  constructor(item, edited$) {
    Object.assign(this, { edited$ });

    this.innerText = item.name;
    this.class = item.done ? "text-muted" : "text-dark";
    this.style = {
      font: "24px 'Helvetica Neue', Helvetica, Arial, sans-serif",
      "text-decoration": item.done ? "line-through" : "",
    };
  }
}

class ItemView {
  tag = "header";
  class = classes.itemViewContainer;
  edited$ = new window.rxjs.BehaviorSubject(false);

  constructor(item, appState) {
    this.children = [
      {
        tag: "button",
        class: classes.itemCheckContainer,
        onclick: () => appState.toggleItem(item.id),
        children: [{ class: item.done ? classes.itemSuccess : "" }],
      },
      {
        source$: this.edited$,
        vdomMap: (edited) =>
            edited
                ? new ItemEditionView(item, appState)
                : new ItemPresentationView(item, this.edited$),
        sideEffects: ({ element }) => element.focus(),
      },
      {
        tag: "i",
        class: classes.itemDelete,
        onclick: () => appState.deleteItem(item.id),
      },
    ];
  }
}

class FooterView {
  tag = "div";
  class = classes.footer;

  constructor(appState) {
    const class$ = (target) => ({
      source$: appState.filterMode$,
      vdomMap: (mode) => (mode === target ? "text-primary" : "text-secondary"),
      wrapper: (d) => `${d} mx-2 fv-pointer btn`,
    });

    this.children = [
      {
        tag: "span",
        innerText: {
          source$: appState.remaining$,
          vdomMap: (items) => items.length,
          wrapper: (d) => `${d} item${d > 1 ? "s" : ""} left`,
        },
      },
      {
        class: "d-flex align-items-center mx-auto",
        children: [
          {
            tag: "button",
            innerText: "All",
            class: class$(Filter.ALL),
            onclick: () => appState.setFilter(Filter.ALL),
          },
          {
            tag: "button",
            innerText: "Active",
            class: class$(Filter.ACTIVE),
            onclick: () => appState.setFilter(Filter.ACTIVE),
          },
          {
            tag: "button",
            innerText: "Completed",
            class: class$(Filter.COMPLETED),
            onclick: () => appState.setFilter(Filter.COMPLETED),
          },
        ],
      },
    ];
  }
}

const urlVue =
    "https://codesandbox.io/s/github/vuejs/vuejs.org/tree/master/src/v2/examples/vue-20-todomvc?from-embed";

class HelpView {
  tag = "div";
  children = [
    {
      tag: "p",
      class: "text-center",
      innerText: "Double click on an item to edit",
    },
    {
      tag: "p",
      class: "text-center",
      innerHTML: `This is a reproduction of the <a target='_blank' href='${urlVue}'> todos example of Vue</a>`,
    },
  ];
}

class AppView {
  tag = "section";
  class = "todo-app";

  constructor(appState) {
    this.children = [
      new HeaderView(appState),
      {
        tag: "div",
        children: {
          policy: "replace",
          source$: appState.selectedItems$,
          vdomMap: (items) => items.map((item) => new ItemView(item, appState)),
        },
      },
      new FooterView(appState),
    ];
  }
}

const state = new AppState();

const div = RxDom.render({
  tag: "div",
  children: [new AppView(state), new HelpView()],
});
document.body.appendChild(div);
