#!/usr/bin/env python3

import ctypes
import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Callable


class PieceTable:
    def __init__(self, lib_path: str = "./libtexteditor.so"):
        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"Shared library not found: {lib_path}")
        self.lib = ctypes.CDLL(lib_path)
        self._setup_function_signatures()
        self.table_ptr = None
    
    def _setup_function_signatures(self):
        self.lib.create_table.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
        self.lib.create_table.restype = ctypes.c_void_p
        self.lib.advance_cursor.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.lib.advance_cursor.restype = None
        self.lib.show_global_cursor.argtypes = [ctypes.c_void_p]
        self.lib.show_global_cursor.restype = ctypes.c_int
        self.lib.show_total_len.argtypes = [ctypes.c_void_p]
        self.lib.show_total_len.restype = ctypes.c_int
        self.lib.add_text.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self.lib.add_text.restype = None
        self.lib.delete_text.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.lib.delete_text.restype = None
        self.lib.extract_current_text.argtypes = [ctypes.c_void_p]
        self.lib.extract_current_text.restype = ctypes.POINTER(ctypes.c_char)
        self.lib.save_current_text.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_int)]
        self.lib.save_current_text.restype = None
    
    def create_from_text(self, text: str, cursor_pos: int = 0):
        text_bytes = text.encode('utf-8') if text else b""
        self.table_ptr = self.lib.create_table(None, text_bytes, cursor_pos)
        if not self.table_ptr:
            raise RuntimeError("Failed to create piece table")
        return self
    
    def create_from_file(self, filename: str, cursor_pos: int = 0):
        self.table_ptr = self.lib.create_table(filename.encode('utf-8'), None, cursor_pos)
        if not self.table_ptr:
            raise RuntimeError(f"Failed to create piece table from {filename}")
        return self
    
    def add_text(self, text: str):
        if not self.table_ptr:
            raise RuntimeError("Piece table not initialized")
        self.lib.add_text(self.table_ptr, text.encode('utf-8'))
    
    def delete_text(self, length: int):
        if not self.table_ptr:
            raise RuntimeError("Piece table not initialized")
        self.lib.delete_text(self.table_ptr, length)
    
    def advance_cursor(self, offset: int):
        if not self.table_ptr:
            raise RuntimeError("Piece table not initialized")
        self.lib.advance_cursor(self.table_ptr, offset)
    
    def get_cursor_position(self) -> int:
        if not self.table_ptr:
            raise RuntimeError("Piece table not initialized")
        return self.lib.show_global_cursor(self.table_ptr)
    
    def get_total_length(self) -> int:
        if not self.table_ptr:
            raise RuntimeError("Piece table not initialized")
        return self.lib.show_total_len(self.table_ptr)
    
    def extract_text(self) -> str:
        if not self.table_ptr:
            raise RuntimeError("Piece table not initialized")
        result_ptr = self.lib.extract_current_text(self.table_ptr)
        if not result_ptr:
            return ""
        text = ctypes.string_at(result_ptr).decode('utf-8')
        return text
    
    def save_to_file(self, filename: str):
        if not self.table_ptr:
            raise RuntimeError("Piece table not initialized")
        self.lib.save_current_text(self.table_ptr, filename.encode('utf-8'), None, None)


class TestRunner:
    def __init__(self):
        self.score = 0
        self.max_score = 100
        self.results = []
        self.pt = None
        self.last_op_duration = 0.0

    def init_piece_table(self):
        try:
            self.pt = PieceTable()
            return True
        except Exception as e:
            self.log_error("Failed to initialize piece table", str(e))
            return False

    def log_result(self, test_name, points, passed, message=""):
        self.results.append({'test': test_name, 'points': points, 'passed': passed, 'message': message})
        if passed:
            self.score += points

    def log_error(self, test_name, error_msg):
        self.log_result(test_name, 0, False, f"ERROR: {error_msg}")

    def run_test_with_files(self, category: str, test_name: str, initial_text: str, 
                          ops_callback: Callable[[PieceTable], None], 
                          expected_text: str, points: int) -> bool:
        try:
            base_dir = Path("test_artifacts") / category
            inputs_dir = base_dir / "inputs"
            refs_dir = base_dir / "references"
            outputs_dir = base_dir / "outputs"
            
            for d in [inputs_dir, refs_dir, outputs_dir]:
                d.mkdir(parents=True, exist_ok=True)

            input_filename = inputs_dir / f"input_{test_name}.txt"
            if input_filename.exists():
                with open(input_filename, 'r') as f:
                    initial_text = f.read()
            else:
                with open(input_filename, 'w') as f:
                    f.write(initial_text)

            ref_filename = refs_dir / f"ref_{test_name}.txt"
            if ref_filename.exists():
                with open(ref_filename, 'r') as f:
                    expected_text = f.read()
            else:
                with open(ref_filename, 'w') as f:
                    f.write(expected_text)
            
            pt = PieceTable().create_from_text(initial_text)
            
            op_start = time.time()
            ops_callback(pt)
            self.last_op_duration = time.time() - op_start
            
            actual_text = pt.extract_text()
            
            out_filename = outputs_dir / f"output_{test_name}.txt"
            with open(out_filename, 'w') as f:
                f.write(actual_text)
            
            if actual_text == expected_text:
                self.log_result(f"{category}/{test_name}", points, True)
                return True
            else:
                self.log_result(f"{category}/{test_name}", points, False, f"Content mismatch")
                return False
                
        except Exception as e:
            self.log_error(f"{category}/{test_name}", str(e))
            return False

    def run_cursor_movement_tests(self):
        points = 10
        try:
            pt = PieceTable().create_from_text("Hello World")
            if pt.get_cursor_position() != 0:
                self.log_result("cursor_init", 0, False, "Initial cursor not 0")
                return
            pt.advance_cursor(5)
            if pt.get_cursor_position() != 5:
                self.log_result("cursor_forward", 0, False, "Failed to move forward")
                return
            pt.advance_cursor(-2)
            if pt.get_cursor_position() != 3:
                self.log_result("cursor_backward", 0, False, "Failed to move backward")
                return
            self.log_result("cursor_movement", points, True)
        except Exception as e:
            self.log_error("cursor_movement", str(e))

    def run_add_text_tests(self):
        category = "adding_text"
        self.run_test_with_files(category, "add_at_start", "World", lambda pt: pt.add_text("Hello "), "Hello World", 4)
        
        def op_end(pt):
            pt.advance_cursor(5)
            pt.add_text(" World")
        self.run_test_with_files(category, "add_at_end", "Hello", op_end, "Hello World", 4)

        def op_middle(pt):
            pt.advance_cursor(5)
            pt.add_text(" beautiful")
        self.run_test_with_files(category, "add_in_middle", "Hello World", op_middle, "Hello beautiful World", 4)

        def op_special(pt):
            pt.advance_cursor(5)
            pt.add_text("\t")
            pt.add_text("\n")
            pt.add_text("!@#$%^&*()")
        self.run_test_with_files(category, "add_special_chars", "Start", op_special, "Start\t\n!@#$%^&*()", 3)

    def run_remove_text_tests(self):
        category = "removing_text"
        
        def op_start(pt):
            pt.advance_cursor(6)
            pt.delete_text(6)
        self.run_test_with_files(category, "remove_from_start", "Hello World", op_start, "World", 3)

        def op_end(pt):
            pt.advance_cursor(11)
            pt.delete_text(6)
        self.run_test_with_files(category, "remove_from_end", "Hello World", op_end, "Hello", 3)

        def op_middle(pt):
            pt.advance_cursor(16)
            pt.delete_text(10)
        self.run_test_with_files(category, "remove_from_middle", "Hello beautiful World", op_middle, "Hello World", 3)

        def op_span(pt):
            pt.advance_cursor(5)
            pt.add_text(" World")
            pt.advance_cursor(-4)
            pt.delete_text(4)
        self.run_test_with_files(category, "remove_spanning_pieces", "Hello", op_span, "Helorld", 3)

        def op_remove_all(pt):
            pt.advance_cursor(9)
            pt.delete_text(9)
        self.run_test_with_files(category, "remove_all", "Delete Me", op_remove_all, "", 3)

    def run_combined_operations_tests(self):
        category = "combined_ops"
        
        def op_typing(pt):
            pt.add_text("The quick brown fox")
            pt.advance_cursor(-3)
            pt.add_text("lazy ")
            pt.advance_cursor(-5)
            pt.delete_text(6)
        self.run_test_with_files(category, "typing_simulation", "", op_typing, "The quick lazy fox", 5)

        def op_replace(pt):
            pt.advance_cursor(11)
            pt.delete_text(4)
            pt.add_text("dogs")
        self.run_test_with_files(category, "replace_text", "I like cats", op_replace, "I like dogs", 5)

        def op_move_edit(pt):
            pt.advance_cursor(1)
            pt.add_text(".")
            pt.advance_cursor(1)
            pt.add_text(".")
            pt.advance_cursor(1)
            pt.add_text(".")
        self.run_test_with_files(category, "move_and_edit", "12345", op_move_edit, "1.2.3.45", 5)

        def op_copy_paste(pt):
            pt.advance_cursor(10)
            pt.add_text(" Copy this.")
        self.run_test_with_files(category, "copy_paste_sim", "Copy this.", op_copy_paste, "Copy this. Copy this.", 5)

        def op_complex(pt):
            pt.advance_cursor(5)
            pt.add_text(" End")
            pt.advance_cursor(-4)
            pt.add_text(" Middle")
            pt.advance_cursor(-7)
            pt.delete_text(5)
            pt.add_text("Beginning")
        self.run_test_with_files(category, "complex_editing", "Start", op_complex, "Beginning Middle End", 5)

    def run_performance_tests(self):
        category = "performance"
        
        base_text_4mb = "x" * (4 * 1024 * 1024)
        NUM_OPS_1 = 30000
        
        def op_load_prepend(pt):
            for _ in range(NUM_OPS_1):
                if pt.get_cursor_position() != 0:
                    pt.advance_cursor(-pt.get_cursor_position())
                pt.add_text("a")
        
        expected_prepend = "a" * NUM_OPS_1 + base_text_4mb
        passed = self.run_test_with_files(category, "load_and_prepend", base_text_4mb, op_load_prepend, expected_prepend, 7)
        duration = self.last_op_duration
        print(f"    [Time: {duration:.3f}s]", flush=True)
        if passed and duration > 1.0:
            self.log_result("performance/load_and_prepend", 7, False, f"Too slow ({duration:.4f}s > 1.0s)")
            self.score -= 7

        NUM_OPS_2 = 30000
        def op_edit_start(pt):
            for _ in range(NUM_OPS_2):
                if pt.get_cursor_position() != 0:
                    pt.advance_cursor(-pt.get_cursor_position())
                pt.add_text("b")
        expected_edit = "b" * NUM_OPS_2 + base_text_4mb
        passed = self.run_test_with_files(category, "edit_large_file_start", base_text_4mb, op_edit_start, expected_edit, 7)
        duration = self.last_op_duration
        print(f"    [Time: {duration:.3f}s]", flush=True)
        if passed and duration > 1.0:
             self.log_result("performance/edit_large_file_start", 7, False, f"Too slow ({duration:.4f}s > 1.0s)")
             self.score -= 7

        base_text_5mb = "y" * (8 * 1024 * 1024)
        NUM_OPS_3 = 12000
        def op_alternating(pt):
            for i in range(NUM_OPS_3):
                if i % 2 == 0:
                    if pt.get_cursor_position() != 0:
                        pt.advance_cursor(-pt.get_cursor_position())
                    pt.add_text("c")
                else:
                    remaining = pt.get_total_length() - pt.get_cursor_position()
                    if remaining > 0:
                        pt.advance_cursor(remaining)
                    pt.add_text("d")
        start_chars = "c" * (NUM_OPS_3 // 2)
        end_chars = "d" * (NUM_OPS_3 // 2)
        expected_alt = start_chars + base_text_5mb + end_chars
        passed = self.run_test_with_files(category, "edit_large_file_random", base_text_5mb, op_alternating, expected_alt, 7)
        duration = self.last_op_duration
        print(f"    [Time: {duration:.3f}s]", flush=True)
        if passed and duration > 0.5:
             self.log_result("performance/edit_large_file_random", 7, False, f"Too slow ({duration:.4f}s > 0.5s)")
             self.score -= 7

        NUM_OPS_4 = 12000
        def op_alternating2(pt):
            for i in range(NUM_OPS_4):
                if i % 2 == 0:
                    if pt.get_cursor_position() != 0:
                        pt.advance_cursor(-pt.get_cursor_position())
                    pt.add_text("e")
                else:
                    remaining = pt.get_total_length() - pt.get_cursor_position()
                    if remaining > 0:
                        pt.advance_cursor(remaining)
                    pt.add_text("f")
        start_chars4 = "e" * (NUM_OPS_4 // 2)
        end_chars4 = "f" * (NUM_OPS_4 // 2)
        expected_alt4 = start_chars4 + base_text_5mb + end_chars4
        passed = self.run_test_with_files(category, "large_sequential_insert_start", base_text_5mb, op_alternating2, expected_alt4, 7)
        duration = self.last_op_duration
        print(f"    [Time: {duration:.3f}s]", flush=True)
        if passed and duration > 0.5:
             self.log_result("performance/large_sequential_insert_start", 7, False, f"Too slow ({duration:.4f}s > 0.5s)")
             self.score -= 7

        NUM_OPS_5 = 12000
        def op_alternating3(pt):
            for i in range(NUM_OPS_5):
                if i % 2 == 0:
                    if pt.get_cursor_position() != 0:
                        pt.advance_cursor(-pt.get_cursor_position())
                    pt.add_text("g")
                else:
                    remaining = pt.get_total_length() - pt.get_cursor_position()
                    if remaining > 0:
                        pt.advance_cursor(remaining)
                    pt.add_text("h")
        start_chars5 = "g" * (NUM_OPS_5 // 2)
        end_chars5 = "h" * (NUM_OPS_5 // 2)
        expected_alt5 = start_chars5 + base_text_5mb + end_chars5
        passed = self.run_test_with_files(category, "large_sequential_delete_start", base_text_5mb, op_alternating3, expected_alt5, 7)
        duration = self.last_op_duration
        print(f"    [Time: {duration:.3f}s]", flush=True)
        if passed and duration > 0.5:
             self.log_result("performance/large_sequential_delete_start", 7, False, f"Too slow ({duration:.4f}s > 0.5s)")
             self.score -= 7

    def run_all_tests(self):
        if not self.init_piece_table():
            return
        self.run_cursor_movement_tests()
        self.run_add_text_tests()
        self.run_remove_text_tests()
        self.run_combined_operations_tests()
        self.run_performance_tests()

    def print_report(self):
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        GREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

        print(f"\n{BOLD}{HEADER}{'='*60}{ENDC}")
        print(f"{BOLD}{HEADER}          Piece Table Test Suite Report{ENDC}")
        print(f"{BOLD}{HEADER}{'='*60}{ENDC}\n")

        categories = {}
        unique_results = {}
        for res in self.results:
            unique_results[res['test']] = res
            
        for res in unique_results.values():
            name_parts = res['test'].split('/')
            cat = name_parts[0] if len(name_parts) > 1 else "General"
            test_name = name_parts[1] if len(name_parts) > 1 else res['test']
            if cat not in categories:
                categories[cat] = {'points': 0, 'total': 0, 'tests': []}
            categories[cat]['tests'].append((test_name, res))
            categories[cat]['points'] += res['points'] if res['passed'] else 0
            categories[cat]['total'] += res['points']

        for cat, data in categories.items():
            print(f"{BOLD}{BLUE}> {cat.replace('_', ' ').title()}{ENDC}")
            for test_name, res in data['tests']:
                display_name = (test_name[:30] + '..') if len(test_name) > 32 else test_name
                pts = str(res['points'])
                if res['passed']:
                    print(f"  {display_name:<34}{GREEN}PASS{ENDC}  {pts}")
                else:
                    print(f"  {display_name:<34}{FAIL}FAIL{ENDC}  {pts}")
                if not res['passed'] and res['message']:
                    print(f"    {FAIL}{res['message']}{ENDC}")
            print()

        print(f"{BOLD}{HEADER}{'='*60}{ENDC}")
        for cat, data in categories.items():
            cat_name = cat.replace('_', ' ').title().ljust(30)
            score = f"{data['points']}".rjust(3)
            total = f"{data['total']}"
            color = GREEN if data['points'] == data['total'] else (WARNING if data['points'] > 0 else FAIL)
            print(f"{cat_name} {color}{score}{ENDC} / {total}")
        print(f"{BOLD}{HEADER}{'='*60}{ENDC}")
        total_color = GREEN if self.score == self.max_score else (WARNING if self.score > 0 else FAIL)
        print(f"{BOLD}TOTAL SCORE                    {total_color}{self.score}{ENDC} / {self.max_score}")
        print(f"{BOLD}{HEADER}{'='*60}{ENDC}\n")


def run_tests():
    old_stdout = os.dup(1)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)
    runner = TestRunner()
    try:
        runner.run_all_tests()
    finally:
        os.dup2(old_stdout, 1)
        os.close(devnull)
        os.close(old_stdout)
    runner.print_report()
    return runner.score


if __name__ == '__main__':
    print("Compiling library...", flush=True)
    result = subprocess.run(['make'], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Build failed:\n{result.stderr}")
        sys.exit(1)
    run_tests()
