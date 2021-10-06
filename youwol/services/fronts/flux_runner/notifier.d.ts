import { Environment } from '@youwol/flux-core';
import { Stream$ } from '@youwol/flux-view';
import { Observable } from 'rxjs';
/**
 * Most of this file is replicated from flux-builder => factorization needed
 */
export declare function plugNotifications(environment: Environment): void;
/**
 * This class provides a notification system that popups message in the
 * HTML document.
 *
 * For now, only module's errors (ModuleError in flux-core) are handled.
 *
 * Notification can be associated to custom [[INotifierAction | action]]
 */
export declare class Notifier {
    static classesIcon: {
        4: string;
        3: string;
    };
    static classesBorder: {
        4: string;
        3: string;
    };
    constructor();
    /**
     * Popup a notification with level=='Info'
     *
     * @param message content
     * @param title title
     * @param actions available actions
     */
    static notify({ message, title, classIcon, timeout }: {
        message?: string | Stream$<unknown, string>;
        classIcon: string | Stream$<unknown, string>;
        title: string;
        timeout?: Observable<any>;
    }): void;
    /**
     * Popup a notification with level=='Error'
     *
     * @param message content
     * @param title title
     * @param actions available actions
     */
    static error({ message, title }: {
        message: string;
        title: string;
    }): void;
    /**
     * Popup a notification with level=='Warning'
     *
     * @param message content
     * @param title title
     * @param actions available actions
     */
    static warning({ message, title }: {
        message: string;
        title: string;
    }): void;
    private static popup;
}
