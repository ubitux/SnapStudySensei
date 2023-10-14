import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

import SnapStudySensei

ApplicationWindow {
    id: root
    title: "SnapStudySensei"
    width: 1280
    height: 800
    visible: true

    signal requestWindowsListRefresh(int current_wid)
    signal selectionMade(rect rect)
    signal wordSelected(string word)
    signal requestRecordAdd(string sentence, string word, string reading, string meaning)
    signal recordRemoved(string record_id)
    signal includeScreenshotToggled(bool value)
    signal audioSourceChanged(string audio_id, string word, string reading)

    function set_capture_window(index) { windowsList.currentIndex = index; }
    function set_sentence(text) { sentenceText.text = text; }
    function set_word_info(info) {
        dictModel.clear();
        for (const entry of info)
            dictModel.append(entry);
        dictView.positionViewAtBeginning();
    }

    function add_records(records) {
        for (const record of records)
            recordModel.append(record);
        recordView.positionViewAtEnd();
    }

    function reset_audio_source() {
        audioNone.checked = true;
        audioSourceChanged("none", "", "");
    }

    function stop_audio() {
        audioPlayer.stop();
        audioPlayer.source = "";
    }

    function play_audio(source) {
        audioPlayer.source = source;
        audioPlayer.play();
    }

    property string selected_word: ""

    WindowCaptureProducer {
        id: windowCaptureProducer
        videoSink: videoOutput.videoSink
    }
    Timer {
        interval: 100; running: true; repeat: true
        onTriggered: windowCaptureProducer.refresh()
    }

    SplitView {
        anchors.fill: parent

        /* Capture + Dictionnary */
        ColumnLayout {
            SplitView.preferredWidth: root.width / 4
            Component.onCompleted: SplitView.minimumWidth = childrenRect.width
            spacing: 0 // managed through the Layout.margins in the children

            /* Capture */
            Frame {
                Layout.fillWidth: true
                Layout.margins: 5

                ColumnLayout {
                    anchors.fill: parent

                    RowLayout {
                        Label { text: "Window:" }
                        ComboBox {
                            id: windowsList
                            model: windowsListModel
                            textRole: "title"
                            valueRole: "wid"
                            Layout.fillWidth: true
                            onActivated: windowCaptureProducer.wid = currentValue
                            Component.onCompleted: windowCaptureProducer.wid = currentValue
                            delegate: ItemDelegate {
                                width: windowsList.width
                                contentItem: Text {
                                    text: modelData[windowsList.textRole]
                                    font.italic: !modelData["visible"]
                                    font.bold: windowsList.currentIndex === index
                                    verticalAlignment: Text.AlignVCenter
                                }
                                highlighted: windowsList.highlightedIndex === index
                            }
                        }
                        Button {
                            text: "↺"
                            background.implicitWidth: 0
                            background.implicitHeight: 0
                            onClicked: requestWindowsListRefresh(windowsList.currentValue)
                        }
                    }
                    VideoOutput {
                        id: videoOutput
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                    }
                    Button {
                        text: "Capture →"
                        onClicked: {
                            captureImage.source = ""; // for a refresh in case the window ID didn't change
                            captureImage.source = "image://snapshot/" + windowCaptureProducer.wid;
                        }
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            /* Dictionary */
            Frame {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: 5
                Layout.topMargin: 0

                ColumnLayout {
                    anchors.fill: parent

                    Label {
                        font.pointSize: 24
                        text: root.selected_word
                        Layout.alignment: Qt.AlignHCenter
                    }
                    ScrollView {
                        Layout.fillHeight: true
                        Layout.fillWidth: true

                        ListView {
                            id: dictView
                            clip: true
                            model: ListModel { id: dictModel }
                            delegate: ColumnLayout {
                                RowLayout {
                                    Button {
                                        text: "✓"
                                        background.implicitWidth: 0
                                        background.implicitHeight: 0
                                        onClicked: {
                                            readingText.text = model.reading != root.selected_word ? model.reading : "";
                                            meaningText.text = model.senses;
                                        }
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        font.pointSize: 18
                                        text: model.rich_title
                                    }
                                }
                                Label {
                                    font.pointSize: 10
                                    text: model.rich_senses
                                }
                            }
                        }
                    }
                }
            }
        }

        /* Card Builder */
        Frame {
            SplitView.preferredWidth: root.width / 2
            Component.onCompleted: SplitView.minimumWidth = childrenRect.width
            Layout.fillWidth: true
            Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent
                Image {
                    id: captureImage
                    cache: false
                    Layout.alignment: Qt.AlignHCenter

                    MouseArea {
                        id: captureMouseArea
                        anchors.fill: parent
                        property point p0
                        property point p1
                        readonly property rect rect: Qt.rect(
                            Math.min(p0.x, p1.x), Math.min(p0.y, p1.y),
                            Math.abs(p0.x - p1.x), Math.abs(p0.y - p1.y)
                        )
                        onPressed: p0 = p1 = Qt.point(mouseX, mouseY)
                        onPositionChanged: p1 = Qt.point(mouseX, mouseY)
                        onReleased: selectionMade(
                            Qt.rect(
                                rect.x / width, rect.y / height,
                                rect.width / width, rect.height / height
                            )
                        )
                    }
                    Rectangle {
                        color: "transparent"
                        border.color: "#58ff51" // TODO: add control?
                        border.width: 2
                        visible: captureMouseArea.rect.width > 0 && captureMouseArea.rect.height > 0
                        x: captureMouseArea.rect.x
                        y: captureMouseArea.rect.y
                        width:  captureMouseArea.rect.width
                        height: captureMouseArea.rect.height
                    }
                }
                Label { text: "Sentence" }
                TextArea {
                    id: sentenceText
                    font.pointSize: 20
                    persistentSelection: true
                    Layout.fillHeight: true
                    Layout.fillWidth: true
                    onReleased: {
                        if (selectedText != "" && selectedText != root.selected_word) {
                            root.selected_word = selectedText;
                            readingText.text = "";
                            meaningText.text = "";
                            reset_audio_source();
                            wordSelected(selectedText);
                        }
                    }
                    background: Rectangle { radius: 2; color: "white"; border.color: "#aaa" }
                }
                Switch {
                    text: "Include screenshot"
                    checked: true
                    onToggled: includeScreenshotToggled(checked)
                }
                GridLayout {
                    columns: 2

                    Label { text: "Word" }
                    TextField {
                        id: wordText
                        text: root.selected_word
                        Layout.fillWidth: true
                        font.pointSize: 20
                        readOnly: true
                    }

                    Label { text: "Reading" }
                    TextField { 
                        id: readingText
                        Layout.fillWidth: true
                        font.pointSize: 20
                    }

                    Label { text: "Meaning" }
                    TextArea {
                        id: meaningText
                        Layout.fillWidth: true
                        background: Rectangle { radius: 2; color: "white"; border.color: "#aaa" }
                    }

                    Label { text: "Audio" }
                    RowLayout {
                        enabled: wordText.text != ""

                        MediaPlayer {
                            id: audioPlayer
                            audioOutput: AudioOutput {}
                        }

                        RadioButton {
                            id: audioNone
                            checked: true
                            text: "None"
                            onClicked: audioSourceChanged("none", "", "")
                        }
                        RadioButton {
                            text: "🔊 Google (Kanji)"
                            onClicked: audioSourceChanged("google-kanji", wordText.text, readingText.text)
                        }
                        RadioButton {
                            text: "🔊 Google (reading)"
                            onClicked: audioSourceChanged("google-reading", wordText.text, readingText.text)
                        }
                        RadioButton {
                            text: "🔊 Pod101"
                            onClicked: audioSourceChanged("pod101", wordText.text, readingText.text)
                        }
                    }
                }

                Button {
                    text: "Record"
                    font.bold: true
                    enabled: wordText.text != "" && meaningText.text != ""
                    Layout.alignment: Qt.AlignHCenter
                    onClicked: requestRecordAdd(sentenceText.text, wordText.text, readingText.text, meaningText.text)
                }
            }
        }

        /* Records */
        Frame {
            SplitView.preferredWidth: root.width / 4
            Layout.fillHeight: true
            Layout.fillWidth: true
            ColumnLayout {
                anchors.fill: parent

                RowLayout {
                    Label { text: "Filter: " }
                    TextField {
                        id: record_filter
                        Layout.fillWidth: true
                        onTextEdited: recordView.positionViewAtBeginning()
                    }
                }
                ListView {
                    id: recordView
                    Layout.fillHeight: true
                    Layout.fillWidth: true
                    model: ListModel { id: recordModel }
                    clip: true
                    Component.onCompleted: positionViewAtEnd()

                    delegate: Loader {
                        readonly property bool __visible: !record_filter.text || model.reading.includes(record_filter.text)
                        sourceComponent: __visible ? visibleRecord : invisibleRecord

                        Component {
                            id: visibleRecord
                            ColumnLayout {
                                RowLayout {
                                    Button {
                                        property string __record_id: model.record_id
                                        text: "✗"
                                        background.implicitWidth: 0
                                        background.implicitHeight: 0
                                        onClicked: {
                                            recordModel.remove(index, 1);
                                            recordRemoved(__record_id);
                                        }
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        font.pointSize: 18
                                        text: model.reading
                                    }
                                }
                                Label {
                                    font.pointSize: 10
                                    font.italic: true
                                    text: model.meaning
                                }
                            }
                        }

                        Component {
                            id: invisibleRecord
                            Item {}
                        }
                    }
                }
            }
        }
    }
}
