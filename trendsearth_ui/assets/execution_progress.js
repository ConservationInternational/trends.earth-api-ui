var dagcomponentfuncs = window.dashAgGridComponentFunctions =
    window.dashAgGridComponentFunctions || {};

dagcomponentfuncs.ExecutionProgress = function (props) {
    var value = props.value;
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 100) {
        return React.createElement("span", null, "\u2014");
    }

    return React.createElement(
        "div",
        { className: "execution-progress" },
        React.createElement("progress", {
            value: value,
            max: 100,
            "aria-label": props.label,
        }),
        React.createElement("span", null, value + "%")
    );
};
