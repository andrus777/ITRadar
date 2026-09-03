DARK_THEME = """
QWidget {
    background-color: #171a21;
    color: #e6e9ef;
    font-family: "Segoe UI";
    font-size: 13px;
}

QFrame#sidebar {
    background-color: #11141a;
    border-right: 1px solid #2a2f3a;
}

QLabel#brand {
    color: #f5f7fb;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 2px;
}

QLabel#brandSubtitle,
QLabel#pageDescription,
QLabel#versionLabel {
    color: #8e98aa;
}

QListWidget#navigationList {
    background: transparent;
    border: none;
    outline: none;
}

QListWidget#navigationList::item {
    border-radius: 6px;
    margin: 2px 0;
    padding: 10px 12px;
}

QListWidget#navigationList::item:hover {
    background-color: #202631;
}

QListWidget#navigationList::item:selected {
    background-color: #294b73;
    color: #ffffff;
}

QLabel#pageTitle {
    color: #f5f7fb;
    font-size: 24px;
    font-weight: 600;
}

QStatusBar#applicationStatusBar {
    background-color: #11141a;
    border-top: 1px solid #2a2f3a;
    color: #aeb7c6;
    padding: 2px 8px;
}
"""
