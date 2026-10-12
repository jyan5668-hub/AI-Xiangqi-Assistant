"""实验4：同一组用例用于初版检查和修订版复测。

所有棋局文件都写入 pytest 临时目录，不会覆盖 data/games.json。
"""

import copy
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app import main


@pytest.fixture(scope="session")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def window(qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "DATA_FILE", tmp_path / "games.json")
    instance = main.MainWindow()
    instance.start_game()
    yield instance
    instance.close()
    instance.deleteLater()
    qt_app.processEvents()


def move(window, source, destination):
    window.board_buttons[source[0]][source[1]].click()
    window.board_buttons[destination[0]][destination[1]].click()


def test_TC01_startup(window):
    """启动后显示 10×9 棋盘、32 枚棋子，红方先行。"""
    assert len(window.board_buttons) == 10
    assert all(len(row) == 9 for row in window.board_buttons)
    assert sum(bool(piece) for row in window.board for piece in row) == 32
    assert window.current_turn == "红方"
    assert not window.moves


def test_TC02_forward_pawn(window):
    """红兵向前一格，更新棋盘、回合和一步记录。"""
    move(window, (6, 0), (5, 0))
    assert window.board[6][0] == ""
    assert window.board[5][0] == "兵"
    assert window.board_buttons[5][0].text() == "兵"
    assert window.current_turn == "黑方"
    assert len(window.moves) == 1


def test_TC03_occupied_square(window):
    """移动到本方棋子所在位置应被拒绝，棋盘和记录不变。"""
    before = copy.deepcopy(window.board)
    move(window, (6, 0), (6, 2))
    assert window.board == before
    assert not window.moves
    assert window.current_turn == "红方"


def test_TC04_save_and_load_in_new_window(window, qt_app):
    """保存后在新窗口恢复局面、回合和棋步。"""
    move(window, (6, 0), (5, 0))
    expected_board = copy.deepcopy(window.board)
    expected_moves = copy.deepcopy(window.moves)
    window.save_game()
    assert main.DATA_FILE.exists()
    saved = json.loads(main.DATA_FILE.read_text(encoding="utf-8"))
    assert saved["board"] == expected_board
    restored = main.MainWindow()
    try:
        restored.load_game()
        assert restored.board == expected_board
        assert restored.moves == expected_moves
        assert restored.current_turn == "黑方"
        assert "读取成功" in restored.status_label.text()
    finally:
        restored.close()
        restored.deleteLater()


def test_TC05_missing_file(window):
    """没有保存文件时提示空数据并保留当前局面。"""
    before = copy.deepcopy(window.board)
    window.load_game()
    assert "暂无历史对局" in window.status_label.text()
    assert window.board == before


def test_TC06_invalid_json(window):
    """JSON 损坏时提示读取失败，保留当前状态。"""
    main.DATA_FILE.write_text("{broken", encoding="utf-8")
    before = copy.deepcopy(window.board)
    window.load_game()
    assert "读取失败" in window.status_label.text()
    assert window.board == before


def test_TC07_invalid_board_size(window):
    """错误尺寸棋盘不能替换当前棋局。"""
    main.DATA_FILE.write_text(json.dumps({"board": [[""]]}), encoding="utf-8")
    before = copy.deepcopy(window.board)
    window.load_game()
    assert "读取失败" in window.status_label.text()
    assert window.board == before


def test_TC08_write_permission_error(window, monkeypatch):
    """模拟文件写入权限失败，保留内存棋局并反馈错误。"""
    move(window, (6, 0), (5, 0))
    before = copy.deepcopy(window.board)

    def deny_write(*args, **kwargs):
        raise PermissionError("test: write permission denied")

    monkeypatch.setattr(main.Path, "write_text", deny_write)
    window.save_game()
    assert "保存失败" in window.status_label.text()
    assert window.board == before
    assert len(window.moves) == 1


def test_TC09_wrong_turn(window):
    """红方回合不能移动黑卒。"""
    before = copy.deepcopy(window.board)
    move(window, (3, 0), (4, 0))
    assert window.board == before, "初版允许红方回合移动黑方棋子"
    assert not window.moves


def test_TC10_pawn_sideways_before_river(window):
    """红兵未过河不能横向移动。"""
    before = copy.deepcopy(window.board)
    move(window, (6, 0), (6, 1))
    assert window.board == before, "初版没有检查兵的移动规则"
    assert not window.moves


def test_TC11_null_board(window):
    """board 为 null 时应反馈格式错误，不能抛出未处理异常。"""
    main.DATA_FILE.write_text('{"board": null}', encoding="utf-8")
    before = copy.deepcopy(window.board)
    window.load_game()
    assert "读取失败" in window.status_label.text()
    assert window.board == before


def test_TC12_data_directory_conflict(window, tmp_path, monkeypatch):
    """数据目录被同名文件占用时，保存应失败并提示而不是崩溃。"""
    conflict = tmp_path / "data-conflict"
    conflict.write_text("occupied", encoding="utf-8")
    monkeypatch.setattr(main, "DATA_DIR", conflict)
    monkeypatch.setattr(main, "DATA_FILE", conflict / "games.json")
    before = copy.deepcopy(window.board)
    window.save_game()
    assert "保存失败" in window.status_label.text()
    assert window.board == before
