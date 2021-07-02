import { Environment } from '@youwol/flux-core';
/**
 * Plug the notification system to the application environment.
 *
 * For now, only module's errors (ModuleError in flux-core) are handled.
 *
 * @param environment application's environment
 */
export declare function plugNotifications(environment: Environment): void;
/**
 * This class provides a notification system that popups message in the
 * HTML document.
 *
 * For now, only module's errors (ModuleError in flux-core) are handled.
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
     */
    static notify({ message, title }: {
        message: any;
        title: any;
    }): void;
    /**
     * Popup a notification with level=='Error'
     *
     * @param message content
     * @param title title
     */
    static error({ message, title }: {
        message: any;
        title: any;
    }): void;
    /**
     * Popup a notification with level=='Warning'
     *
     * @param message content
     * @param title title
     */
    static warning({ message, title }: {
        message: any;
        title: any;
    }): void;
    private static popup;
}
