import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
DATA_FILE = DATA_DIR / "games.json"
LOG_FILE = LOG_DIR / "app.log"
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI象棋对弈助手")
        self.resize(1120, 760)
        self.setMinimumSize(980, 680)

        self.current_turn = "红方"
        self.board = self.initial_board()
        self.sides = self.initial_sides()
        self.selected = None
        self.moves = []
        self.status_label = QLabel("准备开始一局新的对弈")
        self.turn_label = QLabel("红方回合")
        self.board_buttons = []

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(18)
        root.addWidget(self.build_header())

        content = QHBoxLayout()
        content.setSpacing(22)
        content.addWidget(self.build_board_card(), 3)
        content.addWidget(self.build_side_panel(), 2)
        root.addLayout(content, 1)

        footer = QLabel("本地模式 · 棋局数据保存在你的电脑上")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(footer)
        self.apply_styles()

    def build_header(self):
        header = QFrame()
        header.setObjectName("header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 16, 22, 16)
        title_box = QVBoxLayout()
        title = QLabel("AI象棋对弈助手")
        title.setObjectName("title")
        subtitle = QLabel("陪你对弈、分析与复盘的本地学习工具")
        subtitle.setObjectName("subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)
        layout.addStretch()
        badge = QLabel("●  本地练习模式")
        badge.setObjectName("badge")
        layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        return header

    def build_board_card(self):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)
        top = QHBoxLayout()
        heading = QLabel("开始一局对弈")
        heading.setObjectName("section_title")
        hint = QLabel("点击棋子和目标位置进行操作")
        hint.setObjectName("muted")
        top.addWidget(heading)
        top.addStretch()
        top.addWidget(hint)
        layout.addLayout(top)

        board_frame = QFrame()
        board_frame.setObjectName("board_frame")
        board_layout = QGridLayout(board_frame)
        board_layout.setContentsMargins(16, 16, 16, 16)
        board_layout.setSpacing(2)
        for row in range(10):
            row_buttons = []
            for col in range(9):
                button = QPushButton(self.board[row][col])
                button.setObjectName("piece_button")
                button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                button.setMinimumSize(54, 48)
                button.setFont(QFont("Microsoft YaHei", 20, QFont.Weight.Bold))
                button.clicked.connect(lambda checked=False, r=row, c=col: self.cell_clicked(r, c))
                board_layout.addWidget(button, row, col)
                row_buttons.append(button)
            self.board_buttons.append(row_buttons)
        layout.addWidget(board_frame, 1)
        return card

    def build_side_panel(self):
        panel = QVBoxLayout()
        panel.setSpacing(16)

        status_card = QFrame()
        status_card.setObjectName("card")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(22, 20, 22, 20)
        label = QLabel("当前对局")
        label.setObjectName("section_title")
        status_layout.addWidget(label)
        self.turn_label.setObjectName("turn")
        status_layout.addWidget(self.turn_label)
        self.status_label.setObjectName("status")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        panel.addWidget(status_card)

        action_card = QFrame()
        action_card.setObjectName("card")
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(22, 20, 22, 20)
        action_layout.setSpacing(10)
        action_title = QLabel("快捷操作")
        action_title.setObjectName("section_title")
        action_layout.addWidget(action_title)
        start = QPushButton("＋  开始新对弈")
        start.setObjectName("primary_button")
        start.clicked.connect(self.start_game)
        action_layout.addWidget(start)
        for text, callback in (
            ("读取最近棋局", self.load_game),
            ("保存当前棋局", self.save_game),
            ("结束并复盘", self.finish_game),
        ):
            button = QPushButton(text)
            button.setObjectName("secondary_button")
            button.clicked.connect(callback)
            action_layout.addWidget(button)
        panel.addWidget(action_card)

        tip_card = QFrame()
        tip_card.setObjectName("tip_card")
        tip_layout = QVBoxLayout(tip_card)
        tip_layout.setContentsMargins(18, 16, 18, 16)
        tip_title = QLabel("今日提示")
        tip_title.setObjectName("tip_title")
        tip_text = QLabel("先从一个简单局面开始，\n每一步都可以在复盘中回看原因。")
        tip_text.setObjectName("tip_text")
        tip_text.setWordWrap(True)
        tip_layout.addWidget(tip_title)
        tip_layout.addWidget(tip_text)
        panel.addWidget(tip_card)
        panel.addStretch()
        wrapper = QWidget()
        wrapper.setLayout(panel)
        return wrapper

    @staticmethod
    def initial_board():
        board = [["" for _ in range(9)] for _ in range(10)]
        board[0] = list("車馬象士將士象馬車")
        board[2][1], board[2][7] = "炮", "炮"
        for col in (0, 2, 4, 6, 8):
            board[3][col] = "卒"
        board[9] = list("車馬相仕帥仕相馬車")
        board[7][1], board[7][7] = "炮", "炮"
        for col in (0, 2, 4, 6, 8):
            board[6][col] = "兵"
        return board

    @staticmethod
    def initial_sides():
        sides = [[None for _ in range(9)] for _ in range(10)]
        for row in (0, 2, 3):
            for col, piece in enumerate(MainWindow.initial_board()[row]):
                if piece:
                    sides[row][col] = "黑方"
        for row in (9, 7, 6):
            for col, piece in enumerate(MainWindow.initial_board()[row]):
                if piece:
                    sides[row][col] = "红方"
        return sides

    @staticmethod
    def infer_sides(board):
        black_only = {"象", "士", "将", "卒"}
        red_only = {"相", "仕", "帥", "兵"}
        sides = [[None for _ in range(9)] for _ in range(10)]
        for row in range(10):
            for col in range(9):
                piece = board[row][col]
                if piece in black_only:
                    sides[row][col] = "黑方"
                elif piece in red_only:
                    sides[row][col] = "红方"
                elif piece:
                    sides[row][col] = "黑方" if row < 5 else "红方"
        return sides

    def start_game(self):
        self.current_turn = "红方"
        self.board = self.initial_board()
        self.sides = self.initial_sides()
        self.selected = None
        self.moves = []
        self.turn_label.setText("红方回合")
        self.status_label.setText("新对弈已开始，请选择一个棋子")
        self.refresh_board()
        logging.info("start new game")

    def cell_clicked(self, row, col):
        piece = self.board[row][col]
        if self.selected is None:
            if not piece:
                self.status_label.setText("当前状态：请选择一个棋子")
                logging.warning("select empty square row=%s col=%s", row, col)
                return
            if self.sides[row][col] != self.current_turn:
                self.status_label.setText(f"现在是{self.current_turn}回合，不能移动对方棋子")
                logging.warning("move rejected wrong side turn=%s piece_side=%s", self.current_turn, self.sides[row][col])
                return
            self.selected = (row, col)
            self.status_label.setText(f"已选择“{piece}”，请选择目标位置")
            self.refresh_board()
            return

        source_row, source_col = self.selected
        if (source_row, source_col) == (row, col):
            self.selected = None
            self.status_label.setText("已取消选择")
            self.refresh_board()
            return

        if piece and self.sides[row][col] == self.current_turn:
            self.status_label.setText("目标位置已有棋子，请选择空位置")
            logging.warning("move rejected occupied square row=%s col=%s", row, col)
            return

        moving_piece = self.board[source_row][source_col]
        side = self.sides[source_row][source_col]
        if not self.is_legal_move(moving_piece, side, source_row, source_col, row, col):
            self.status_label.setText(f"{moving_piece}不能这样移动，请检查走法")
            logging.warning("move rejected by piece rule piece=%s side=%s from=%s to=%s", moving_piece, side, [source_row, source_col], [row, col])
            return
        self.board[row][col] = moving_piece
        self.board[source_row][source_col] = ""
        self.sides[row][col] = side
        self.sides[source_row][source_col] = None
        self.moves.append({
            "piece": moving_piece,
            "from": [source_row, source_col],
            "to": [row, col],
            "time": datetime.now().isoformat(timespec="seconds"),
        })
        self.selected = None
        self.current_turn = "黑方" if self.current_turn == "红方" else "红方"
        self.turn_label.setText(f"{self.current_turn}回合")
        self.status_label.setText(f"走子成功：{moving_piece} 已移动")
        logging.info("move piece=%s from=%s to=%s", moving_piece, [source_row, source_col], [row, col])
        self.refresh_board()

    def is_legal_move(self, piece, side, sr, sc, tr, tc):
        dr, dc = tr - sr, tc - sc
        row_distance, col_distance = abs(dr), abs(dc)
        target_piece = self.board[tr][tc]
        if target_piece and self.sides[tr][tc] == side:
            return False

        def clear_path():
            row_step = (dr > 0) - (dr < 0)
            col_step = (dc > 0) - (dc < 0)
            row, col = sr + row_step, sc + col_step
            blockers = 0
            while (row, col) != (tr, tc):
                blockers += bool(self.board[row][col])
                row += row_step
                col += col_step
            return blockers

        if piece in {"兵", "卒"}:
            forward = -1 if side == "红方" else 1
            crossed_river = sr <= 4 if side == "红方" else sr >= 5
            return (dc == 0 and dr == forward) or (
                crossed_river and dr == 0 and col_distance == 1
            )
        if piece == "車":
            return (dr == 0 or dc == 0) and clear_path() == 0
        if piece == "馬":
            if (row_distance, col_distance) not in {(1, 2), (2, 1)}:
                return False
            leg = (sr + (1 if dr > 0 else -1), sc) if row_distance == 2 else (sr, sc + (1 if dc > 0 else -1))
            return not self.board[leg[0]][leg[1]]
        if piece == "炮":
            if not (dr == 0 or dc == 0):
                return False
            blockers = clear_path()
            return blockers == (1 if target_piece else 0)
        if piece in {"相", "象"}:
            if row_distance != 2 or col_distance != 2:
                return False
            if side == "红方" and tr < 5 or side == "黑方" and tr > 4:
                return False
            return not self.board[(sr + tr) // 2][(sc + tc) // 2]
        if piece in {"仕", "士"}:
            palace_rows = range(7, 10) if side == "红方" else range(0, 3)
            return row_distance == 1 and col_distance == 1 and tr in palace_rows and 3 <= tc <= 5
        if piece in {"帥", "將"}:
            palace_rows = range(7, 10) if side == "红方" else range(0, 3)
            if tr in palace_rows and 3 <= tc <= 5 and row_distance + col_distance == 1:
                return True
            if dc == 0 and target_piece in {"帥", "將"}:
                return clear_path() == 0
            return False
        return False

    def refresh_board(self):
        for row in range(10):
            for col in range(9):
                button = self.board_buttons[row][col]
                piece = self.board[row][col]
                button.setText(piece)
                if (row, col) == self.selected:
                    button.setStyleSheet("font-size: 20px; font-weight: bold; color: #762f25; background: #ffd36e; border: 3px solid #c45d3e; border-radius: 5px;")
                else:
                    button.setStyleSheet("font-size: 20px; font-weight: bold; color: #762f25; background: #fff4d6; border: 1px solid #c9894f; border-radius: 5px;")

    def save_game(self):
        try:
            DATA_DIR.mkdir(exist_ok=True)
            game_data = {
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "current_turn": self.current_turn,
                "moves": self.moves,
                "board": self.board,
                "sides": self.sides,
            }
            DATA_FILE.write_text(json.dumps(game_data, ensure_ascii=False, indent=2), encoding="utf-8")
            self.status_label.setText("棋局保存成功：data/games.json")
            logging.info("save game successfully moves=%s", len(self.moves))
        except OSError as exc:
            self.status_label.setText(f"保存失败：{exc}")
            logging.exception("save game failed")

    def load_game(self):
        if not DATA_FILE.exists():
            self.status_label.setText("暂无历史对局，请先开始并保存一局")
            logging.warning("load requested but data file does not exist")
            return
        try:
            game_data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            board = game_data["board"]
            if (
                not isinstance(board, list)
                or len(board) != 10
                or any(not isinstance(row, list) or len(row) != 9 for row in board)
                or any(not isinstance(piece, str) for row in board for piece in row)
            ):
                raise ValueError("棋盘数据尺寸不正确")
            sides = game_data.get("sides") or self.infer_sides(board)
            if (
                not isinstance(sides, list)
                or len(sides) != 10
                or any(not isinstance(row, list) or len(row) != 9 for row in sides)
                or any(side not in {None, "红方", "黑方"} for row in sides for side in row)
            ):
                raise ValueError("棋子所属方数据格式不正确")
            moves = game_data.get("moves", [])
            if not isinstance(moves, list):
                raise ValueError("棋步记录格式不正确")
            self.board = board
            self.sides = sides
            self.moves = moves
            self.current_turn = game_data.get("current_turn", "红方")
            self.selected = None
            self.turn_label.setText(f"{self.current_turn}回合")
            self.status_label.setText(f"棋局读取成功：共 {len(self.moves)} 步")
            logging.info("load game successfully moves=%s", len(self.moves))
            self.refresh_board()
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            self.status_label.setText(f"读取失败：{exc}")
            logging.exception("load game failed")

    def finish_game(self):
        self.status_label.setText(f"复盘已生成：本局共 {len(self.moves)} 步，可继续练习")
        logging.info("finish game moves=%s", len(self.moves))

    @staticmethod
    def apply_styles():
        QApplication.instance().setStyleSheet("""
            QWidget#central { background: #f3f6f8; }
            QFrame#header, QFrame#card { background: white; border: 1px solid #e1e8ec; border-radius: 16px; }
            QFrame#header { background: #17324d; border: none; }
            QLabel#title { color: white; font-size: 27px; font-weight: 700; }
            QLabel#subtitle { color: #b9ccda; font-size: 13px; margin-top: 4px; }
            QLabel#badge { color: #d9f7e8; background: #245b4a; border-radius: 12px; padding: 8px 12px; font-size: 12px; }
            QLabel#section_title { color: #17324d; font-size: 18px; font-weight: 700; }
            QLabel#muted, QLabel#footer { color: #71808b; font-size: 12px; }
            QLabel#turn { color: #b24b32; background: #fff1eb; border-radius: 10px; padding: 10px; font-size: 16px; font-weight: 700; }
            QLabel#status { color: #536771; background: #f5f8fa; border-radius: 10px; padding: 12px; font-size: 13px; }
            QFrame#board_frame { background: #e9bf7a; border: 5px solid #9b5a31; border-radius: 12px; }
            QPushButton#piece_button { color: #762f25; background: #fff4d6; border: 1px solid #c9894f; border-radius: 5px; }
            QPushButton#piece_button:hover { background: #ffe5ad; }
            QPushButton#primary_button { color: white; background: #c45d3e; border: none; border-radius: 9px; padding: 12px; font-size: 14px; font-weight: 700; }
            QPushButton#primary_button:hover { background: #a94d33; }
            QPushButton#secondary_button { color: #245878; background: #eef5f8; border: 1px solid #d5e3e9; border-radius: 9px; padding: 10px; font-size: 13px; }
            QPushButton#secondary_button:hover { background: #dcebf2; }
            QFrame#tip_card { background: #fff8e8; border: 1px solid #f0d9a6; border-radius: 14px; }
            QLabel#tip_title { color: #8b5b20; font-size: 14px; font-weight: 700; }
            QLabel#tip_text { color: #7b684b; font-size: 13px; }
        """)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
