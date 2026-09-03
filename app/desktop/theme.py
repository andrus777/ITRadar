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

QLabel#sectionTitle {
    color: #cbd3df;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}

QFrame#kpiCard,
QFrame#systemStatus {
    background-color: #20242d;
    border: 1px solid #303744;
    border-radius: 8px;
}

QLabel#kpiLabel,
QLabel#kpiDetail,
QLabel#statusDetail,
QLabel#dashboardFeedback {
    color: #8e98aa;
}

QLabel#kpiValue {
    color: #f5f7fb;
    font-size: 25px;
    font-weight: 650;
}

QFrame#systemStatus[state="ok"] QLabel#statusIndicator { color: #43c781; }
QFrame#systemStatus[state="warning"] QLabel#statusIndicator { color: #f0b44c; }
QFrame#systemStatus[state="failure"] QLabel#statusIndicator { color: #ef6262; }
QFrame#systemStatus[state="disabled"] QLabel#statusIndicator { color: #697386; }

QPushButton#secondaryButton {
    background-color: #294b73;
    border: 1px solid #39638f;
    border-radius: 6px;
    color: #ffffff;
    padding: 7px 15px;
}

QPushButton#secondaryButton:hover { background-color: #345d89; }
QPushButton#secondaryButton:disabled { color: #7f8999; background-color: #252b34; }

QTableWidget#opportunitiesTable {
    background-color: #1b1f27;
    alternate-background-color: #1f242d;
    border: 1px solid #303744;
    border-radius: 7px;
    gridline-color: #2a303b;
    selection-background-color: #294b73;
}

QTableWidget#opportunitiesTable::item { padding: 7px; }

QHeaderView::section {
    background-color: #252a34;
    border: none;
    border-right: 1px solid #353c48;
    border-bottom: 1px solid #353c48;
    color: #aeb7c6;
    font-weight: 600;
    padding: 8px;
}

QStatusBar#applicationStatusBar {
    background-color: #11141a;
    border-top: 1px solid #2a2f3a;
    color: #aeb7c6;
    padding: 2px 8px;
}
"""
