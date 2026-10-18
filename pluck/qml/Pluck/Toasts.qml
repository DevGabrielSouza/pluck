pragma Singleton
import QtQuick

QtObject {
    signal requested(string tone, string title, string message, string actionText, var action)

    function show(tone, title, message, actionText, action) {
        requested(tone, title, message || "", actionText || "", action || null)
    }
}
