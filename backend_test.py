#!/usr/bin/env python3
"""
Backend API Testing for PDF Bot
Tests all API endpoints and PDF processing functionality
"""

import requests
import sys
import os
import tempfile
import json
from datetime import datetime
from pathlib import Path

# Import PDF processor for direct testing
sys.path.append('/app/backend')
from pdf_processor import process_pdf, get_pdf_info, compress_pdf, resize_to_a4

class PDFBotAPITester:
    def __init__(self, base_url="https://compress-pdf-bot.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    {details}")

    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test("Health endpoint", True, f"Status: {data}")
                    return True
                else:
                    self.log_test("Health endpoint", False, f"Unexpected response: {data}")
                    return False
            else:
                self.log_test("Health endpoint", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Health endpoint", False, f"Error: {str(e)}")
            return False

    def test_stats_endpoint(self):
        """Test /api/stats endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/stats", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["total_processed", "total_bytes_saved", "total_bytes_saved_mb", "bot_status"]
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.log_test("Stats endpoint", False, f"Missing fields: {missing_fields}")
                    return False
                
                # Validate data types
                if (isinstance(data["total_processed"], int) and 
                    isinstance(data["total_bytes_saved"], int) and
                    isinstance(data["total_bytes_saved_mb"], (int, float)) and
                    isinstance(data["bot_status"], str)):
                    self.log_test("Stats endpoint", True, f"Data: {data}")
                    return True
                else:
                    self.log_test("Stats endpoint", False, f"Invalid data types: {data}")
                    return False
            else:
                self.log_test("Stats endpoint", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Stats endpoint", False, f"Error: {str(e)}")
            return False

    def test_logs_endpoint(self):
        """Test /api/logs endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/logs", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Logs endpoint", True, f"Returned {len(data)} logs")
                    return True
                else:
                    self.log_test("Logs endpoint", False, f"Expected array, got: {type(data)}")
                    return False
            else:
                self.log_test("Logs endpoint", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Logs endpoint", False, f"Error: {str(e)}")
            return False

    def create_test_pdf(self, filename="test.pdf"):
        """Create a simple test PDF for processing tests"""
        try:
            import fitz  # PyMuPDF
            
            # Create temp file
            fd, temp_path = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            
            # Create a simple PDF with text
            doc = fitz.open()
            page = doc.new_page(width=612, height=792)  # Letter size
            page.insert_text((50, 50), "Test PDF for compression and resizing", fontsize=12)
            page.insert_text((50, 100), "This is a test document with some content.", fontsize=10)
            
            # Add more content to make it larger
            for i in range(10):
                page.insert_text((50, 150 + i*20), f"Line {i+1}: Some additional content to increase file size", fontsize=10)
            
            doc.save(temp_path)
            doc.close()
            
            return temp_path
            
        except Exception as e:
            print(f"Error creating test PDF: {e}")
            return None

    def test_pdf_compression(self):
        """Test PDF compression functionality"""
        test_pdf = self.create_test_pdf()
        if not test_pdf:
            self.log_test("PDF Compression", False, "Could not create test PDF")
            return False
        
        try:
            # Create output file
            fd, output_path = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            
            # Test compression
            success = compress_pdf(test_pdf, output_path)
            
            if success and os.path.exists(output_path):
                original_size = os.path.getsize(test_pdf)
                compressed_size = os.path.getsize(output_path)
                
                self.log_test("PDF Compression", True, 
                             f"Original: {original_size} bytes, Compressed: {compressed_size} bytes")
                
                # Cleanup
                os.remove(output_path)
                return True
            else:
                self.log_test("PDF Compression", False, "Compression failed")
                return False
                
        except Exception as e:
            self.log_test("PDF Compression", False, f"Error: {str(e)}")
            return False
        finally:
            if test_pdf and os.path.exists(test_pdf):
                os.remove(test_pdf)

    def test_pdf_a4_resize(self):
        """Test PDF A4 resizing functionality"""
        test_pdf = self.create_test_pdf()
        if not test_pdf:
            self.log_test("PDF A4 Resize", False, "Could not create test PDF")
            return False
        
        try:
            # Create output file
            fd, output_path = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            
            # Test A4 resize
            success = resize_to_a4(test_pdf, output_path)
            
            if success and os.path.exists(output_path):
                # Verify A4 dimensions
                import fitz
                doc = fitz.open(output_path)
                page = doc[0]
                width = page.rect.width
                height = page.rect.height
                doc.close()
                
                # A4 dimensions are 595x842 points
                if abs(width - 595) < 1 and abs(height - 842) < 1:
                    self.log_test("PDF A4 Resize", True, 
                                 f"Resized to {width:.1f}x{height:.1f} (A4: 595x842)")
                else:
                    self.log_test("PDF A4 Resize", False, 
                                 f"Wrong dimensions: {width:.1f}x{height:.1f}, expected 595x842")
                
                # Cleanup
                os.remove(output_path)
                return True
            else:
                self.log_test("PDF A4 Resize", False, "Resize failed")
                return False
                
        except Exception as e:
            self.log_test("PDF A4 Resize", False, f"Error: {str(e)}")
            return False
        finally:
            if test_pdf and os.path.exists(test_pdf):
                os.remove(test_pdf)

    def test_full_pdf_processing(self):
        """Test complete PDF processing pipeline"""
        test_pdf = self.create_test_pdf()
        if not test_pdf:
            self.log_test("Full PDF Processing", False, "Could not create test PDF")
            return False
        
        try:
            # Create output file
            fd, output_path = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            
            # Test full processing
            success, error_msg = process_pdf(test_pdf, output_path)
            
            if success and os.path.exists(output_path):
                # Get info about processed file
                info = get_pdf_info(output_path)
                
                self.log_test("Full PDF Processing", True, 
                             f"Processed successfully: {info['pages']} pages, {info['size_mb']} MB")
                
                # Cleanup
                os.remove(output_path)
                return True
            else:
                self.log_test("Full PDF Processing", False, f"Processing failed: {error_msg}")
                return False
                
        except Exception as e:
            self.log_test("Full PDF Processing", False, f"Error: {str(e)}")
            return False
        finally:
            if test_pdf and os.path.exists(test_pdf):
                os.remove(test_pdf)

    def run_all_tests(self):
        """Run all backend tests"""
        print("🔍 Starting PDF Bot Backend Tests...")
        print(f"Testing API at: {self.base_url}")
        print("-" * 50)
        
        # API Tests
        print("\n📡 API Endpoint Tests:")
        self.test_health_endpoint()
        self.test_stats_endpoint()
        self.test_logs_endpoint()
        
        # PDF Processing Tests
        print("\n📄 PDF Processing Tests:")
        self.test_pdf_compression()
        self.test_pdf_a4_resize()
        self.test_full_pdf_processing()
        
        # Summary
        print("\n" + "="*50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print("❌ Some tests failed!")
            return False

def main():
    tester = PDFBotAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    results_file = "/app/backend_test_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "summary": {
                "total_tests": tester.tests_run,
                "passed_tests": tester.tests_passed,
                "success_rate": round((tester.tests_passed / tester.tests_run) * 100, 1) if tester.tests_run > 0 else 0,
                "timestamp": datetime.now().isoformat()
            },
            "detailed_results": tester.test_results
        }, f, indent=2)
    
    print(f"\n📝 Detailed results saved to: {results_file}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())