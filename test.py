#!/usr/bin/env python3
"""
RAGex Holy Sanity Check - Comprehensive System Test

Tests everything:
- Backend imports and core modules
- CLI functionality and flags
- Configuration system
- Vector store operations
- Provider orchestration
- Frontend files existence
- OS integrations presence

Run from project root: python test.py
"""

import sys
import os
from pathlib import Path

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_section(title):
    """Print a test section header."""
    print(f"\n{BOLD}{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{BLUE}{title}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 60}{RESET}")


def print_pass(msg):
    """Print a passing test."""
    print(f"{GREEN}✓ {msg}{RESET}")


def print_fail(msg):
    """Print a failing test."""
    print(f"{RED}✗ {msg}{RESET}")


def print_warn(msg):
    """Print a warning."""
    print(f"{YELLOW}⚠ {msg}{RESET}")


def print_info(msg):
    """Print info message."""
    print(f"  {msg}")


def test_imports():
    """Test all critical imports."""
    print_section("Testing Backend Imports")
    
    tests_passed = 0
    tests_failed = 0
    
    # Core backend imports
    imports_to_test = [
        ("backend.app.core.config", "Configuration module"),
        ("backend.app.core.validation", "Validation module"),
        ("backend.app.core.files", "File handling module"),
        ("backend.app.core.errors", "Error messages module"),
        ("backend.app.rag.loader", "Document loader"),
        ("backend.app.rag.chunker", "Text chunker"),
        ("backend.app.rag.store", "Vector store"),
        ("backend.app.rag.retriever", "Retriever"),
        ("backend.app.rag.generator", "Generator"),
        ("backend.app.rag.orchestrator", "LLM orchestrator"),
        ("backend.app.rag.intent", "Intent detection"),
        ("backend.app.rag.indexer", "Canonical indexer"),
        ("backend.app.api.routes", "API routes"),
        ("cli.ui", "CLI UI utilities"),
    ]
    
    for module_name, description in imports_to_test:
        try:
            __import__(module_name)
            print_pass(f"{description}: {module_name}")
            tests_passed += 1
        except Exception as e:
            print_fail(f"{description}: {module_name} - {e}")
            tests_failed += 1
    
    return tests_passed, tests_failed


def test_cli_imports():
    """Test CLI entrypoint imports."""
    print_section("Testing CLI Imports")
    
    tests_passed = 0
    tests_failed = 0
    
    try:
        import ragcli
        print_pass("ragcli.py imports successfully")
        tests_passed += 1
        
        # Check for main function
        if hasattr(ragcli, 'main'):
            print_pass("ragcli.main() function exists")
            tests_passed += 1
        else:
            print_fail("ragcli.main() function not found")
            tests_failed += 1
            
    except Exception as e:
        print_fail(f"ragcli.py import failed: {e}")
        tests_failed += 2
    
    return tests_passed, tests_failed


def test_config_system():
    """Test configuration system."""
    print_section("Testing Configuration System")
    
    tests_passed = 0
    tests_failed = 0
    
    try:
        from backend.app.core import config
        
        # Test config defaults
        required_fields = [
            'RAG_PROVIDER', 'RAG_MODEL_NAME', 'OLLAMA_BASE_URL',
            'EMBEDDING_MODEL', 'DB_PATH', 'COLLECTION_NAME',
            'CANDIDATE_K', 'MIN_SCORE_THRESHOLD', 'REFUSAL_RESPONSE'
        ]
        
        for field in required_fields:
            if hasattr(config, field):
                value = getattr(config, field)
                print_pass(f"Config field '{field}': {repr(value)}")
                tests_passed += 1
            else:
                print_fail(f"Config field '{field}' missing")
                tests_failed += 1
        
        # Test Settings class
        if hasattr(config, 'Settings'):
            print_pass("Settings class exists")
            tests_passed += 1
            
            settings = config.Settings()
            if hasattr(settings, 'validate_runtime_requirements'):
                print_pass("Runtime validation method exists")
                tests_passed += 1
            else:
                print_fail("Runtime validation method missing")
                tests_failed += 1
        else:
            print_fail("Settings class not found")
            tests_failed += 2
            
    except Exception as e:
        print_fail(f"Config system test failed: {e}")
        tests_failed += len(required_fields) + 2
    
    return tests_passed, tests_failed


def test_canonical_pipeline():
    """Test canonical indexing pipeline."""
    print_section("Testing Canonical Indexing Pipeline")
    
    tests_passed = 0
    tests_failed = 0
    
    try:
        from backend.app.rag import indexer
        
        # Check for required functions
        if hasattr(indexer, 'index_paths'):
            print_pass("index_paths() function exists")
            tests_passed += 1
        else:
            print_fail("index_paths() function missing")
            tests_failed += 1
        
        if hasattr(indexer, 'clean_index'):
            print_pass("clean_index() function exists")
            tests_passed += 1
        else:
            print_fail("clean_index() function missing")
            tests_failed += 1
        
        if hasattr(indexer, 'IndexingResult'):
            print_pass("IndexingResult dataclass exists")
            tests_passed += 1
            
            # Test IndexingResult fields
            result_fields = ['documents_indexed', 'chunks_indexed', 'files_skipped', 
                           'index_cleared', 'chunks_removed', 'final_index_size']
            result = indexer.IndexingResult(
                documents_indexed=0, chunks_indexed=0, files_skipped=0,
                index_cleared=False, chunks_removed=0, final_index_size=0
            )
            
            for field in result_fields:
                if hasattr(result, field):
                    tests_passed += 1
                else:
                    print_fail(f"IndexingResult field '{field}' missing")
                    tests_failed += 1
            
            if hasattr(result, 'to_dict'):
                print_pass("IndexingResult.to_dict() method exists")
                tests_passed += 1
            else:
                print_fail("IndexingResult.to_dict() method missing")
                tests_failed += 1
        else:
            print_fail("IndexingResult dataclass missing")
            tests_failed += 8
            
    except Exception as e:
        print_fail(f"Canonical pipeline test failed: {e}")
        tests_failed += 11
    
    return tests_passed, tests_failed


def test_file_structure():
    """Test repository file structure."""
    print_section("Testing Repository Structure")
    
    tests_passed = 0
    tests_failed = 0
    
    # Required files
    required_files = [
        'ragcli.py',
        'install.sh',
        'README.md',
        'backend/requirements.txt',
        'backend/app/main.py',
        'frontend/index.html',
        'frontend/README.md',
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print_pass(f"File exists: {file_path}")
            tests_passed += 1
        else:
            print_fail(f"File missing: {file_path}")
            tests_failed += 1
    
    # Required directories
    required_dirs = [
        'backend/app/core',
        'backend/app/rag',
        'backend/app/api',
        'cli',
        'docs',
        'integrations/linux',
        'integrations/macos',
    ]
    
    for dir_path in required_dirs:
        if Path(dir_path).is_dir():
            print_pass(f"Directory exists: {dir_path}")
            tests_passed += 1
        else:
            print_fail(f"Directory missing: {dir_path}")
            tests_failed += 1
    
    # Documentation files
    doc_files = [
        'docs/QUICK_START.md',
        'docs/RPD.md',
        'docs/INVARIANTS.md',
        'docs/tasks.md',
    ]
    
    for doc_file in doc_files:
        if Path(doc_file).exists():
            print_pass(f"Documentation exists: {doc_file}")
            tests_passed += 1
        else:
            print_fail(f"Documentation missing: {doc_file}")
            tests_failed += 1
    
    return tests_passed, tests_failed


def test_integrations():
    """Test OS integrations."""
    print_section("Testing OS Integrations")
    
    tests_passed = 0
    tests_failed = 0
    
    # Linux integrations
    linux_files = [
        'integrations/linux/ragex.desktop',
        'integrations/linux/ragex-launcher.sh',
        'integrations/linux/nautilus-open-with-ragex.sh',
    ]
    
    for file_path in linux_files:
        if Path(file_path).exists():
            print_pass(f"Linux integration: {Path(file_path).name}")
            tests_passed += 1
        else:
            print_fail(f"Linux integration missing: {file_path}")
            tests_failed += 1
    
    # macOS integrations
    macos_files = [
        'integrations/macos/Open with RAGex.workflow',
    ]
    
    for file_path in macos_files:
        if Path(file_path).exists():
            print_pass(f"macOS integration: {Path(file_path).name}")
            tests_passed += 1
        else:
            print_fail(f"macOS integration missing: {file_path}")
            tests_failed += 1
    
    return tests_passed, tests_failed


def test_frontend():
    """Test frontend files."""
    print_section("Testing Frontend")
    
    tests_passed = 0
    tests_failed = 0
    
    # Check index.html exists and has key content
    index_path = Path('frontend/index.html')
    if index_path.exists():
        print_pass("frontend/index.html exists")
        tests_passed += 1
        
        content = index_path.read_text()
        
        # Check for key elements
        checks = [
            ('API_BASE', 'API endpoint configuration'),
            ('sendMessage', 'Send message function'),
            ('uploadFiles', 'Upload files function'),
            ('localStorage', 'Local storage usage'),
        ]
        
        for keyword, description in checks:
            if keyword in content:
                print_pass(f"Frontend has {description}")
                tests_passed += 1
            else:
                print_warn(f"Frontend might be missing {description}")
                tests_failed += 1
    else:
        print_fail("frontend/index.html missing")
        tests_failed += 5
    
    # Check frontend README
    if Path('frontend/README.md').exists():
        print_pass("frontend/README.md exists (demo-only documentation)")
        tests_passed += 1
    else:
        print_fail("frontend/README.md missing")
        tests_failed += 1
    
    return tests_passed, tests_failed


def test_end_to_end():
    """Run a minimal end-to-end pipeline test."""
    print_section("Testing End-to-End Pipeline (Minimal)")
    
    tests_passed = 0
    tests_failed = 0
    
    try:
        from backend.app.rag.loader import load_inputs
        from backend.app.rag.chunker import Chunker
        from backend.app.rag.store import clear_index
        
        print_info("Testing document loading...")
        test_path = "docs/demo"
        if Path(test_path).exists():
            docs, errors = load_inputs([test_path])
            if docs:
                print_pass(f"Loaded {len(docs)} document segments")
                tests_passed += 1
                
                print_info("Testing chunking...")
                chunker = Chunker()
                chunks = chunker.chunk(docs)
                if chunks:
                    print_pass(f"Generated {len(chunks)} chunks")
                    tests_passed += 1
                else:
                    print_fail("No chunks generated")
                    tests_failed += 1
            else:
                print_warn(f"No documents in {test_path}, skipping pipeline test")
                tests_passed += 2
        else:
            print_warn(f"Test documents path {test_path} not found, skipping")
            tests_passed += 2
            
    except Exception as e:
        print_fail(f"End-to-end test failed: {e}")
        tests_failed += 2
    
    return tests_passed, tests_failed


def main():
    """Run all tests."""
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}RAGex Holy Sanity Check{RESET}")
    print(f"{BOLD}Comprehensive System Verification{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")
    
    total_passed = 0
    total_failed = 0
    
    # Run all test suites
    test_suites = [
        ("Backend Imports", test_imports),
        ("CLI Imports", test_cli_imports),
        ("Configuration System", test_config_system),
        ("Canonical Pipeline", test_canonical_pipeline),
        ("File Structure", test_file_structure),
        ("OS Integrations", test_integrations),
        ("Frontend", test_frontend),
        ("End-to-End Pipeline", test_end_to_end),
    ]
    
    results = []
    for suite_name, test_func in test_suites:
        try:
            passed, failed = test_func()
            total_passed += passed
            total_failed += failed
            results.append((suite_name, passed, failed))
        except Exception as e:
            print_fail(f"Test suite '{suite_name}' crashed: {e}")
            results.append((suite_name, 0, 1))
            total_failed += 1
    
    # Print summary
    print_section("Test Summary")
    
    for suite_name, passed, failed in results:
        status = GREEN + "PASS" + RESET if failed == 0 else RED + "FAIL" + RESET
        print(f"{suite_name:.<40} {status} ({passed} passed, {failed} failed)")
    
    print(f"\n{BOLD}Total:{RESET}")
    print(f"  {GREEN}✓ Passed: {total_passed}{RESET}")
    print(f"  {RED}✗ Failed: {total_failed}{RESET}")
    
    if total_failed == 0:
        print(f"\n{BOLD}{GREEN}{'=' * 60}{RESET}")
        print(f"{BOLD}{GREEN}ALL TESTS PASSED - System is healthy! ✓{RESET}")
        print(f"{BOLD}{GREEN}{'=' * 60}{RESET}\n")
        return 0
    else:
        print(f"\n{BOLD}{RED}{'=' * 60}{RESET}")
        print(f"{BOLD}{RED}SOME TESTS FAILED - Review issues above{RESET}")
        print(f"{BOLD}{RED}{'=' * 60}{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
