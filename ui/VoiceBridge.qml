import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Window {
    id: window
    width: 680
    height: bridge.expanded ? 434 : 180
    visible: false
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
    title: "VoiceBridge"

    component GlassCombo: ComboBox {
        id: control
        height: 30
        font.pixelSize: 12
        background: Rectangle {
            radius: 0
            color: "#0B0F14"
            border.color: control.activeFocus ? "#58A6FF" : "#2A3B55"
            border.width: 1
        }
        contentItem: Text {
            leftPadding: 10
            text: control.displayText
            color: "#E6EDF3"
            font.pixelSize: 12
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        indicator: Text {
            x: control.width - width - 10
            y: control.topPadding + (control.availableHeight - height) / 2
            text: "▾"
            color: "#8B9BB3"
            font.pixelSize: 11
        }
        delegate: ItemDelegate {
            width: control.width
            height: 28
            contentItem: Text {
                text: modelData
                color: "#E6EDF3"
                font.pixelSize: 12
                verticalAlignment: Text.AlignVCenter
                leftPadding: 10
                elide: Text.ElideRight
            }
            background: Rectangle {
                radius: 0
                color: highlighted ? "#26344A" : "transparent"
            }
        }
        popup: Popup {
            y: control.height + 4
            width: control.width
            implicitHeight: Math.min(contentItem.implicitHeight + 10, 260)
            padding: 4
            background: Rectangle {
                color: "#101722"
                radius: 0
                border.color: "#30363D"
                border.width: 1
            }
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: control.popup.visible ? control.delegateModel : null
                currentIndex: control.highlightedIndex
                ScrollIndicator.vertical: ScrollIndicator { }
            }
        }
    }

    component GlassCheck: CheckBox {
        id: control
        font.pixelSize: 11
        contentItem: Text {
            text: control.text
            color: "#C8D4E6"
            font.pixelSize: 11
            leftPadding: control.indicator.width + 6
            verticalAlignment: Text.AlignVCenter
        }
        indicator: Rectangle {
            implicitWidth: 15
            implicitHeight: 15
            radius: 0
            color: control.checked ? "#58A6FF" : "#0B0F14"
            border.color: control.checked ? "#58A6FF" : "#2A3B55"
            border.width: 1
            Text {
                anchors.centerIn: parent
                text: "✓"
                visible: control.checked
                color: "#071019"
                font.pixelSize: 10
                font.bold: true
            }
        }
        spacing: 4
    }

    component GlassSlider: Slider {
        id: control
        background: Rectangle {
            x: control.leftPadding
            y: control.topPadding + control.availableHeight / 2 - height / 2
            width: control.availableWidth
            height: 4
            radius: 0
            color: "#26344A"
            Rectangle {
                width: control.visualPosition * parent.width
                height: 4
                radius: 0
                color: "#58A6FF"
            }
        }
        handle: Rectangle {
            x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
            y: control.topPadding + control.availableHeight / 2 - height / 2
            width: 14
            height: 14
            radius: 7
            color: "#E6EDF3"
            border.color: "#58A6FF"
            border.width: 1
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: 0
        antialiasing: true
        color: Qt.rgba(0.03, 0.05, 0.08, bridge.windowAlpha)
        border.color: "#2A3B55"
        border.width: 1
    }

    ShaderEffect {
        id: glass
        anchors.fill: parent
        property real time: 0
        property vector2d resolution: Qt.vector2d(width, height)
        fragmentShader: "
            varying highp vec2 qt_TexCoord0;
            uniform highp float qt_Opacity;
            uniform highp float time;
            uniform highp vec2 resolution;

            float roundedBox(vec2 p, vec2 b, float r) {
                vec2 q = abs(p) - b + vec2(r);
                return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
            }

            void main() {
                vec2 uv = qt_TexCoord0;
                vec2 p = (uv - 0.5) * resolution;
                float d = roundedBox(p, resolution * 0.5 - vec2(1.0), 0.0);
                float inside = 1.0 - smoothstep(-1.0, 1.0, d);
                float edge = smoothstep(2.0, 0.0, abs(d));
                float t = time * 0.08;
                float band = exp(-pow((uv.x + uv.y * 0.45 - fract(t)) * 5.0, 2.0));
                vec3 color = vec3(0.55, 0.75, 1.0) * edge * 0.20;
                color += vec3(0.35, 0.65, 1.0) * band * 0.08;
                float alpha = inside * (edge * 0.20 + band * 0.08);
                gl_FragColor = vec4(color, alpha) * qt_Opacity;
            }
        "
        NumberAnimation on time {
            from: 0
            to: 100
            duration: 90000
            loops: Animation.Infinite
            running: window.visible
        }
    }

    Item {
        id: content
        anchors.fill: parent
        anchors.margins: 16

        Item {
            id: header
            width: parent.width
            height: 44

            Row {
                id: brand
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10

                Text {
                    text: "VoiceBridge"
                    color: "#F3F7FF"
                    font.family: "Segoe UI"
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }

                Rectangle {
                    width: 66
                    height: 22
                    radius: 0
                    color: bridge.statusKind === "ready" ? "#173D2B"
                         : bridge.statusKind === "error" ? "#4A1D24"
                         : bridge.statusKind === "starting" ? "#4A3B18"
                         : "#252B35"
                    border.color: bridge.statusKind === "ready" ? "#2C6B49"
                                : bridge.statusKind === "error" ? "#7A2C37"
                                : bridge.statusKind === "starting" ? "#7A6128"
                                : "#3A4350"
                    border.width: 1
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: bridge.statusKind === "ready" ? "READY"
                            : bridge.statusKind === "error" ? "ERROR"
                            : bridge.statusKind === "starting" ? "STARTING"
                            : "OFFLINE"
                        color: bridge.statusKind === "ready" ? "#73E3A4"
                             : bridge.statusKind === "error" ? "#FF8A98"
                             : bridge.statusKind === "starting" ? "#F0C674"
                             : "#9AA8BF"
                        font.pixelSize: 9
                        font.bold: true
                        font.family: "Segoe UI"
                    }
                }
            }

            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                Item {
                    width: 28
                    height: 28
                    Canvas {
                        anchors.centerIn: parent
                        width: 18
                        height: 18
                        onPaint: {
                            var ctx = getContext("2d");
                            ctx.strokeStyle = "#A9B7CC";
                            ctx.fillStyle = "#A9B7CC";
                            ctx.lineWidth = 1.4;
                            ctx.lineCap = "round";
                            var ys = [3, 9, 15];
                            var xs = [7, 12, 5];
                            for (var i = 0; i < 3; i++) {
                                ctx.beginPath();
                                ctx.moveTo(1, ys[i]);
                                ctx.lineTo(17, ys[i]);
                                ctx.stroke();
                                ctx.beginPath();
                                ctx.arc(xs[i], ys[i], 2, 0, Math.PI * 2);
                                ctx.fill();
                            }
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: bridge.toggleExpanded()
                    }
                }

                Text {
                    text: "—"
                    color: "#A9B7CC"
                    font.pixelSize: 16
                    width: 24
                    height: 28
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: bridge.hideWindow()
                    }
                }

                Text {
                    text: "×"
                    color: "#A9B7CC"
                    font.pixelSize: 17
                    width: 24
                    height: 28
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: bridge.closeApp()
                    }
                }
            }

            DragHandler {
                target: null
                acceptedButtons: Qt.LeftButton
                onActiveChanged: {
                    if (active) {
                        window.startSystemMove();
                    } else {
                        bridge.saveWindowPosition(window.x, window.y);
                    }
                }
            }
        }

        Item {
            id: inputRow
            y: 52
            width: parent.width
            height: 52

            TextField {
                id: input
                width: parent.width - 62
                height: 52
                placeholderText: "输入文字，Enter 发送…"
                color: "#EEF5FF"
                placeholderTextColor: "#72809A"
                font.family: "Microsoft YaHei UI"
                font.pixelSize: 15
                leftPadding: 16
                rightPadding: 16
                selectByMouse: true
                onAccepted: window.sendMessage()
                background: Rectangle {
                    radius: 0
                    color: Qt.rgba(0.03, 0.05, 0.08, Math.min(1.0, bridge.windowAlpha + 0.02))
                    border.color: input.activeFocus ? "#58A6FF" : "#2A3B55"
                    border.width: 1
                }
            }

            Rectangle {
                id: sendButton
                x: parent.width - 52
                width: 52
                height: 52
                radius: 0
                color: input.text.trim().length > 0 ? "#58A6FF" : "#1A2433"
                border.color: input.text.trim().length > 0 ? "#79C0FF" : "#2A3B55"
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "↑"
                    color: input.text.trim().length > 0 ? "#071019" : "#637188"
                    font.pixelSize: 24
                    font.bold: true
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: window.sendMessage()
                }
            }
        }

        Item {
            id: voiceRow
            y: 112
            width: parent.width
            height: 32

            Row {
                id: voiceLeft
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                Canvas {
                    width: 16
                    height: 16
                    anchors.verticalCenter: parent.verticalCenter
                    onPaint: {
                        var ctx = getContext("2d");
                        ctx.fillStyle = "#8B9BB3";
                        ctx.beginPath();
                        ctx.arc(8, 4.5, 2.5, 0, Math.PI * 2);
                        ctx.fill();
                        ctx.beginPath();
                        ctx.arc(8, 12, 5, Math.PI, 0, false);
                        ctx.fill();
                    }
                }

                Text {
                    text: bridge.currentVoice.length > 0 ? bridge.currentVoice : "选择声音"
                    color: "#C8D4E6"
                    font.family: "Microsoft YaHei UI"
                    font.pixelSize: 12
                    width: Math.min(430, implicitWidth)
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: bridge.expanded ? "▴" : "▾"
                    color: "#8B9BB3"
                    font.pixelSize: 11
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            MouseArea {
                anchors.fill: voiceLeft
                cursorShape: Qt.PointingHandCursor
                onClicked: bridge.toggleExpanded()
            }

            Text {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: "Enter 发送 · Ctrl+Alt+T 隐藏"
                color: "#7F8DA3"
                font.family: "Microsoft YaHei UI"
                font.pixelSize: 10
            }
        }

        Item {
            id: settings
            y: 152
            width: parent.width
            height: 250
            visible: bridge.expanded

            Rectangle {
                anchors.fill: parent
                radius: 0
                color: Qt.rgba(0.05, 0.08, 0.12, bridge.windowAlpha * 0.83)
                border.color: "#26344A"
                border.width: 1
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
                    spacing: 8

                    Text {
                        text: "ENGINE"
                        Layout.preferredWidth: 52
                        color: "#7F8DA3"
                        font.pixelSize: 9
                        font.bold: true
                    }
                    GlassCombo {
                        id: engineCombo
                        Layout.preferredWidth: 205
                        Layout.preferredHeight: 30
                        model: bridge.engines
                        onActivated: bridge.setEngine(currentIndex)
                        Component.onCompleted: currentIndex = bridge.engineIndex
                    }
                    Text {
                        text: "OPACITY"
                        Layout.preferredWidth: 48
                        color: "#7F8DA3"
                        font.pixelSize: 9
                        font.bold: true
                    }
                    GlassSlider {
                        id: opacitySlider
                        Layout.preferredWidth: 80
                        Layout.preferredHeight: 28
                        from: 0.25
                        to: 1.0
                        stepSize: 0.05
                        value: bridge.windowAlpha
                        onMoved: bridge.setWindowAlpha(value)
                    }
                    Text {
                        Layout.preferredWidth: 30
                        text: Math.round(opacitySlider.value * 100) + "%"
                        color: "#C8D4E6"
                        font.pixelSize: 11
                    }
                    Text {
                        text: "SPEED"
                        Layout.preferredWidth: 36
                        color: "#7F8DA3"
                        font.pixelSize: 9
                        font.bold: true
                    }
                    GlassSlider {
                        id: speedSlider
                        Layout.preferredWidth: 90
                        Layout.preferredHeight: 28
                        from: 0.5
                        to: 2.0
                        stepSize: 0.05
                        value: bridge.speed
                        onMoved: bridge.setSpeed(value)
                    }
                    Text {
                        Layout.preferredWidth: 32
                        text: speedSlider.value.toFixed(2)
                        color: "#C8D4E6"
                        font.pixelSize: 11
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
                    spacing: 8
                    Text {
                        text: "VOICE"
                        Layout.preferredWidth: 52
                        color: "#7F8DA3"
                        font.pixelSize: 9
                        font.bold: true
                    }
                    GlassCombo {
                        id: voiceCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        model: bridge.voices
                        onActivated: bridge.setVoice(currentIndex)
                        Component.onCompleted: currentIndex = bridge.voiceIndex
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
                    spacing: 8
                    GlassCheck {
                        text: "OUTPUT"
                        Layout.preferredWidth: 82
                        checked: bridge.outputEnabled
                        onToggled: bridge.setFlag("output", checked)
                    }
                    GlassCombo {
                        id: outputCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        enabled: bridge.outputEnabled
                        model: bridge.outputs
                        onActivated: bridge.setOutput(currentIndex)
                        Component.onCompleted: currentIndex = bridge.outputIndex
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
                    spacing: 8
                    GlassCheck {
                        text: "LISTENIN"
                        Layout.preferredWidth: 82
                        checked: bridge.monitor
                        onToggled: bridge.setFlag("monitor", checked)
                    }
                    GlassCombo {
                        id: monitorCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        enabled: bridge.monitor
                        model: bridge.outputs
                        onActivated: bridge.setMonitorIndex(currentIndex)
                        Component.onCompleted: currentIndex = bridge.monitorIndex
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 24
                    spacing: 12
                    GlassCheck {
                        text: "聊天框文字"
                        checked: bridge.chatbox
                        onToggled: bridge.setFlag("chatbox", checked)
                    }
                    GlassCheck {
                        text: "打字指示"
                        checked: bridge.typing
                        onToggled: bridge.setFlag("typing", checked)
                    }
                    GlassCheck {
                        text: "发送后隐藏"
                        checked: bridge.hideAfterSend
                        onToggled: bridge.setFlag("hideAfterSend", checked)
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 18
                    spacing: 8
                    Rectangle {
                        width: 6
                        height: 6
                        radius: 3
                        color: bridge.statusKind === "ready" ? "#3FB950"
                             : bridge.statusKind === "error" ? "#F85149"
                             : bridge.statusKind === "starting" ? "#D29922"
                             : "#8B949E"
                    }
                    Text {
                        Layout.fillWidth: true
                        text: bridge.statusText
                        color: "#8B9BB3"
                        font.family: "Microsoft YaHei UI"
                        font.pixelSize: 9
                        elide: Text.ElideRight
                    }
                    Text {
                        text: input.text.length + "/" + bridge.maxChars
                        color: "#72809A"
                        font.pixelSize: 9
                    }
                }
            }
        }
    }

    function sendMessage() {
        var value = input.text;
        if (value.trim().length === 0) {
            return;
        }
        if (bridge.send(value)) {
            input.clear();
        }
        input.forceActiveFocus();
    }

    Connections {
        target: bridge
        function onFocusInput() {
            input.forceActiveFocus();
        }
        function onEngineIndexChanged() {
            engineCombo.currentIndex = bridge.engineIndex;
        }
        function onVoiceIndexChanged() {
            voiceCombo.currentIndex = bridge.voiceIndex;
        }
        function onVoicesChanged() {
            voiceCombo.currentIndex = bridge.voiceIndex;
        }
        function onOutputIndexChanged() {
            outputCombo.currentIndex = bridge.outputIndex;
        }
        function onMonitorIndexChanged() {
            monitorCombo.currentIndex = bridge.monitorIndex;
        }
        function onOutputsChanged() {
            outputCombo.currentIndex = bridge.outputIndex;
            monitorCombo.currentIndex = bridge.monitorIndex;
        }
        function onSpeedChanged() {
            speedSlider.value = bridge.speed;
        }
        function onWindowAlphaChanged() {
            opacitySlider.value = bridge.windowAlpha;
        }
    }
}
