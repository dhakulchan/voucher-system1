"""
Passport MRZ OCR Processor
Extracts passport information from images using MRZ (Machine Readable Zone)
Compliant with PDPA - no permanent storage, masked logging
"""

import cv2
import numpy as np
import pytesseract
import re
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
import tempfile
import os
from PIL import Image, ExifTags

logger = logging.getLogger(__name__)

class PassportMRZProcessor:
    """Process passport images and extract MRZ data"""
    
    # MRZ line patterns
    MRZ_LINE1_PATTERN = r'^P[A-Z<]{1}[A-Z]{3}[A-Z<]{39}$'
    MRZ_LINE2_PATTERN = r'^[A-Z0-9<]{44}$'
    
    # Field extraction patterns
    PASSPORT_NUMBER_PATTERN = r'[A-Z0-9]{6,9}'
    DATE_PATTERN = r'\d{6}'  # YYMMDD
    
    # Country codes mapping (ISO 3166-1 alpha-3)
    COUNTRY_CODES = {
        'THA': 'Thailand', 'USA': 'United States', 'GBR': 'United Kingdom',
        'CHN': 'China', 'JPN': 'Japan', 'KOR': 'South Korea',
        'DEU': 'Germany', 'FRA': 'France', 'AUS': 'Australia',
        'CAN': 'Canada', 'SGP': 'Singapore', 'MYS': 'Malaysia',
        'IDN': 'Indonesia', 'PHL': 'Philippines', 'VNM': 'Vietnam',
        'IND': 'India', 'HKG': 'Hong Kong', 'TWN': 'Taiwan'
    }
    
    def __init__(self):
        """Initialize processor with aggressive Tesseract configuration for MRZ"""
        # Aggressive OCR config for MRZ:
        # -l eng: FORCE English only (critical for Thai/Asian passports)
        # --oem 3: LSTM neural net mode
        # --psm 6: Assume uniform block of text
        # tessedit_char_whitelist: Only MRZ valid characters
        self.tesseract_config = (
            '-l eng --oem 3 --psm 6 '
            '-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789< '
            '-c preserve_interword_spaces=0'
        )
        # Increase PIL image size limit to handle high-res photos
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = 200000000  # 200M pixels
    
    def _fix_image_orientation(self, image_path: str) -> np.ndarray:
        """
        Fix image orientation based on EXIF data (important for mobile photos)
        Returns OpenCV image with correct orientation
        """
        try:
            # Open with PIL to read EXIF
            pil_image = Image.open(image_path)
            
            # Try to get EXIF orientation using newer API first
            orientation = None
            try:
                exif = pil_image.getexif()
                if exif:
                    # Orientation tag is 274
                    orientation = exif.get(274, None)
            except:
                # Fallback to older API
                exif_data = pil_image._getexif() if hasattr(pil_image, '_getexif') else None
                if exif_data:
                    for tag, value in exif_data.items():
                        if tag in ExifTags.TAGS and ExifTags.TAGS[tag] == 'Orientation':
                            orientation = value
                            break
            
            # Apply orientation correction
            if orientation:
                logger.info(f"EXIF Orientation tag: {orientation}")
                if orientation == 3:
                    pil_image = pil_image.rotate(180, expand=True)
                    logger.info("✅ Rotated image 180° based on EXIF")
                elif orientation == 6:
                    pil_image = pil_image.rotate(270, expand=True)
                    logger.info("✅ Rotated image 270° (CCW) based on EXIF")
                elif orientation == 8:
                    pil_image = pil_image.rotate(90, expand=True)
                    logger.info("✅ Rotated image 90° (CW) based on EXIF")
                else:
                    logger.info(f"EXIF orientation {orientation} - no rotation needed")
            else:
                logger.info("No EXIF orientation tag found")
            
            # Convert PIL to OpenCV format
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            return cv_image
            
        except Exception as e:
            logger.warning(f"EXIF orientation fix failed, using default: {e}")
            # Fallback to regular CV2 read
            return cv2.imread(image_path)
        
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Smart preprocessing - gentler for high-res images, aggressive for low-res
        - EXIF orientation fix (for mobile photos)
        - Smart downscaling for very large images
        - CLAHE contrast enhancement
        - Adaptive denoising based on image size
        - Smart thresholding
        - Minimal morphological operations
        - Smart upscaling for small images
        """
        try:
            # Fix orientation first (important for mobile cameras)
            img = self._fix_image_orientation(image_path)
            if img is None:
                raise ValueError(f"Cannot read image: {image_path}")
            
            # Get original dimensions
            orig_height, orig_width = img.shape[:2]
            logger.info(f"Original image size: {orig_width}x{orig_height} ({orig_width*orig_height/1000000:.1f}M pixels)")
            
            # Smart downscaling for very large images (over 4000px)
            # Large images can cause over-processing and lose detail
            if orig_height > 4000 or orig_width > 4000:
                max_dim = 3000
                if orig_height > orig_width:
                    scale = max_dim / orig_height
                else:
                    scale = max_dim / orig_width
                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)
                img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
                logger.info(f"Downscaled large image to {new_width}x{new_height} for better processing")
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            height, width = gray.shape[:2]
            is_high_res = height > 2000 or width > 2000
            
            # 1. CLAHE for contrast enhancement (gentler for high-res)
            clip_limit = 2.0 if is_high_res else 3.0
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # 2. Smart denoising - gentler for high-res images
            if is_high_res:
                # Light denoising for high-res (preserve detail)
                denoised = cv2.fastNlMeansDenoising(enhanced, None, h=5, templateWindowSize=7, searchWindowSize=15)
                logger.info("Applied light denoising (high-res image)")
            else:
                # More aggressive for low-res
                denoised = cv2.fastNlMeansDenoising(enhanced, None, h=10, templateWindowSize=7, searchWindowSize=21)
                logger.info("Applied aggressive denoising (low-res image)")
            
            # 3. Light sharpening (only for low-res)
            if not is_high_res:
                kernel_sharpening = np.array([[-1, -1, -1],
                                              [-1,  9, -1],
                                              [-1, -1, -1]])
                sharpened = cv2.filter2D(denoised, -1, kernel_sharpening)
            else:
                sharpened = denoised
            
            # 4. Deskew image
            deskewed = self._deskew_image(sharpened)
            
            # 5. Smart thresholding
            if is_high_res:
                # Use larger block size for high-res images
                binary = cv2.adaptiveThreshold(
                    deskewed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, blockSize=25, C=10
                )
            else:
                binary = cv2.adaptiveThreshold(
                    deskewed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, blockSize=15, C=8
                )
            
            # 6. Minimal morphological operations (too much destroys text)
            kernel = np.ones((1, 1), np.uint8)
            morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
            
            # 7. Smart scaling for OCR
            height, width = morph.shape[:2]
            if height < 800:
                # Upscale small images
                scale = 1200 / height
                new_width = int(width * scale)
                morph = cv2.resize(morph, (new_width, 1200), interpolation=cv2.INTER_CUBIC)
                logger.info(f"Upscaled to {new_width}x1200 for better OCR")
            elif height > 3000:
                # Downscale very large images for faster OCR
                scale = 2000 / height
                new_width = int(width * scale)
                morph = cv2.resize(morph, (new_width, 2000), interpolation=cv2.INTER_AREA)
                logger.info(f"Downscaled to {new_width}x2000 for faster OCR")
            
            logger.info(f"Smart preprocessing completed (final size: {morph.shape[1]}x{morph.shape[0]})")
            return morph
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            raise
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Deskew image using Hough transform - only small angle corrections"""
        try:
            # Detect edges
            edges = cv2.Canny(image, 50, 150, apertureSize=3)
            
            # Detect lines
            lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
            
            if lines is not None and len(lines) > 0:
                # Calculate average angle
                angles = []
                for rho, theta in lines[:10, 0]:
                    angle = np.degrees(theta) - 90
                    # Filter out large rotations (likely wrong detection)
                    # Only consider small skew angles
                    if abs(angle) < 45:
                        angles.append(angle)
                
                if not angles:
                    logger.info("No small skew angles detected, image likely already oriented")
                    return image
                
                median_angle = np.median(angles)
                
                # Only rotate for small angle corrections (< 15 degrees)
                # Large rotations (45-90°) suggest wrong detection, not skew
                if 0.5 < abs(median_angle) < 15:
                    (h, w) = image.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                    rotated = cv2.warpAffine(image, M, (w, h), 
                                           flags=cv2.INTER_CUBIC, 
                                           borderMode=cv2.BORDER_REPLICATE)
                    logger.info(f"Deskewed image by {median_angle:.2f} degrees")
                    return rotated
                else:
                    logger.info(f"Skipped large rotation ({median_angle:.2f}°), image already oriented by EXIF")
            
            return image
            
        except Exception as e:
            logger.warning(f"Deskewing failed, using original: {e}")
            return image
    
    def _preprocess_mrz_only(self, mrz_gray: np.ndarray) -> np.ndarray:
        """
        Gentle preprocessing specifically for MRZ region only
        Less aggressive than full passport preprocessing
        """
        try:
            height, width = mrz_gray.shape[:2]
            logger.info(f"Preprocessing MRZ region: {width}x{height}")
            
            # 1. Light CLAHE for contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(mrz_gray)
            
            # 2. Very light denoising to preserve text clarity
            denoised = cv2.fastNlMeansDenoising(enhanced, None, h=3, templateWindowSize=7, searchWindowSize=15)
            
            # 3. Try OTSU thresholding first (works better for scanned docs)
            _, otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 4. Fallback to adaptive if OTSU fails
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, blockSize=31, C=10
            )
            
            # Use OTSU if it looks better (more white pixels = likely better)
            if np.sum(otsu == 255) > np.sum(binary == 255) * 0.5:
                cleaned = otsu
                logger.info("Using OTSU thresholding")
            else:
                cleaned = binary
                logger.info("Using adaptive thresholding")
            
            # 5. Minimal morphology - just close small gaps
            kernel = np.ones((1, 2), np.uint8)
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=1)
            
            # 6. DON'T scale if already large enough (>150px height)
            # Scaling can introduce artifacts
            if height < 150:
                scale = 200 / height
                new_width = int(width * scale)
                cleaned = cv2.resize(cleaned, (new_width, 200), interpolation=cv2.INTER_CUBIC)
                logger.info(f"Upscaled MRZ to {new_width}x200 for OCR")
            elif height > 400:
                # Only downscale if VERY large
                scale = 350 / height
                new_width = int(width * scale)
                cleaned = cv2.resize(cleaned, (new_width, 350), interpolation=cv2.INTER_AREA)
                logger.info(f"Downscaled MRZ to {new_width}x350 for OCR")
            else:
                logger.info(f"Keeping MRZ at original size: {width}x{height}")
            
            logger.info(f"MRZ preprocessing complete: final size {cleaned.shape[1]}x{cleaned.shape[0]}")
            return cleaned
            
        except Exception as e:
            logger.error(f"MRZ preprocessing failed: {e}")
            return mrz_gray
    
    def extract_mrz_region(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract MRZ region from passport image
        MRZ is typically at the bottom of the passport
        Try multiple extraction strategies
        """
        try:
            height, width = image.shape[:2]
            
            # Strategy 1: Simple bottom crop (most reliable for focused MRZ photos)
            # If user focused on MRZ as instructed, just take bottom 30-40%
            simple_mrz = image[int(height * 0.6):height, :]
            
            # Strategy 2: Contour-based extraction (for full passport scans)
            # MRZ is usually in bottom 20% of image
            search_region = image[int(height * 0.7):height, :]
            
            # Find text regions using contours
            contours, _ = cv2.findContours(
                cv2.bitwise_not(search_region), 
                cv2.RETR_EXTERNAL, 
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            if contours:
                # Find largest contour (likely MRZ)
                largest_contour = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest_contour)
                
                # Only use contour-based if it's substantial
                if w > width * 0.5 and h > 50:  # At least 50% width and 50px height
                    # Extract MRZ with padding
                    padding = 20
                    mrz_cropped = search_region[
                        max(0, y-padding):min(search_region.shape[0], y+h+padding),
                        max(0, x-padding):min(search_region.shape[1], x+w+padding)
                    ]
                    logger.info(f"MRZ region extracted via contours: {w}x{h}")
                    return mrz_cropped
            
            # Fallback to simple bottom crop
            logger.info(f"Using simple bottom crop for MRZ ({simple_mrz.shape[1]}x{simple_mrz.shape[0]})")
            return simple_mrz
            
        except Exception as e:
            logger.error(f"Error extracting MRZ region: {e}")
            return None
    
    def ocr_mrz(self, mrz_image: np.ndarray) -> list:
        """
        Multi-strategy OCR on MRZ region with better preprocessing
        Returns list of cleaned text lines
        """
        try:
            best_lines = []
            best_score = 0
            
            # Ensure MRZ image is reasonable size for OCR
            height, width = mrz_image.shape[:2]
            original_mrz = mrz_image.copy()  # Keep original for minimal processing attempts
            
            if height < 100:  # Too small
                scale = 300 / height
                new_width = int(width * scale)
                mrz_image = cv2.resize(mrz_image, (new_width, 300), interpolation=cv2.INTER_CUBIC)
                original_mrz = mrz_image.copy()
                logger.info(f"Upscaled MRZ to {new_width}x300 for OCR")
            
            # Try multiple preprocessing variations - START WITH MINIMAL PROCESSING
            variations = [
                ('minimal', original_mrz),  # Try the least processed version first
                ('minimal_inv', cv2.bitwise_not(original_mrz)),
            ]
            
            # Light contrast enhancement only
            clahe_light = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            light_enhanced = clahe_light.apply(original_mrz)
            variations.extend([
                ('light_contrast', light_enhanced),
                ('light_contrast_inv', cv2.bitwise_not(light_enhanced))
            ])
            
            # Only if minimal doesn't work, try more processing
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(mrz_image)
            variations.extend([
                ('enhanced', enhanced),
                ('enhanced_inv', cv2.bitwise_not(enhanced))
            ])
            
            for name, img in variations:
                # Try multiple PSM modes for different text layouts
                # IMPORTANT: Add -l eng to force English language
                psm_configs = [
                    ('-l eng --oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789< -c preserve_interword_spaces=0', 'psm6'),
                    ('-l eng --oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789< -c preserve_interword_spaces=0', 'psm7'),
                    ('-l eng --oem 3 --psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<', 'psm13'),
                ]
                
                for config, config_name in psm_configs:
                    # Run Tesseract OCR
                    text = pytesseract.image_to_string(img, config=config)
                    
                    # DEBUG: Log raw OCR output
                    char_count = len(text.strip())
                    if char_count > 10:  # Only log if we got substantial text
                        logger.info(f"OCR ({name}/{config_name}): {char_count} chars")
                        # Log first 100 chars to see what OCR sees
                        if char_count > 50:
                            logger.info(f"  First 100 chars: {text[:100].replace(chr(10), ' | ')}")
                    
                    # Split into lines and clean
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    # Clean lines: remove all spaces
                    cleaned_lines = []
                    for line in lines:
                        cleaned = line.replace(' ', '')
                        if len(cleaned) >= 35:  # Log potential MRZ lines (lowered from 40)
                            logger.info(f"OCR ({name}/{config_name}) line: '{line[:60]}' (len={len(cleaned)})")
                        # MRZ lines should be 44 characters (TD3 format)
                        # VERY LENIENT: accept 35-50 chars for poor quality images
                        if 35 <= len(cleaned) <= 50:
                            # Basic validation: MRZ should have mix of letters, digits
                            has_letters = any(c.isalpha() for c in cleaned)
                            has_digits = any(c.isdigit() for c in cleaned)
                            
                            if has_letters and has_digits:  # At minimum need both
                                cleaned_lines.append(cleaned)
                
                    # Score based on:
                    # 1. Number of lines (want exactly 2)
                    # 2. Line lengths (closer to 44 is better)
                    # 3. Character validity (more alphanumeric + '<' is better)
                    # 4. BONUS: Contains valid country code (HUGE bonus!)
                    # 5. BONUS: MRZ pattern (digits + letters in specific pattern)
                    score = 0
                    if len(cleaned_lines) >= 1:
                        # Base score for having lines
                        score += 50 * len(cleaned_lines)
                        if len(cleaned_lines) >= 2:
                            score += 50  # Extra bonus for 2+ lines
                        
                        for line in cleaned_lines[:2]:
                            # Length score
                            score += (44 - abs(44 - len(line))) * 2
                            # Valid character score
                            valid_chars = sum(c.isalnum() or c == '<' for c in line)
                            score += valid_chars
                            
                            # HUGE BONUS: Contains valid country code (1000 points!)
                            has_country_code = False
                            for i in range(len(line) - 2):
                                if line[i:i+3] in self.COUNTRY_CODES:
                                    score += 1000
                                    has_country_code = True
                                    logger.info(f"🎯 COUNTRY CODE BONUS +1000: '{line[i:i+3]}' in: {line[:60]}")
                                    break
                            
                            # Additional bonus: MRZ Line 2 pattern (passport# + country + dates)
                            # Line 2 format: PASSPORT#(9) + COUNTRY(3) + DOB(6) + SEX(1) + EXPIRY(6) + ...
                            if len(line) >= 20 and has_country_code:
                                digit_count = sum(c.isdigit() for c in line[:20])
                                # MRZ Line 2 should have ~15 digits in first 20 chars
                                if digit_count >= 12:
                                    score += 500
                                    logger.info(f"🎯 MRZ PATTERN BONUS +500: {digit_count} digits in first 20 chars")
                    
                    if score > best_score:
                        best_score = score
                        best_lines = cleaned_lines
                        logger.info(f"✨ Better OCR result from '{name}/{config_name}' (score: {score}, lines: {len(cleaned_lines)})")
            
            if best_lines:
                logger.info(f"OCR extracted {len(best_lines)} MRZ lines (after cleaning)")
                # Log cleaned MRZ lines for debugging
                for i, line in enumerate(best_lines, 1):
                    logger.info(f"  Cleaned MRZ Line {i}: {line}")
            else:
                logger.warning("No valid MRZ lines found in OCR output")
            
            return best_lines
            
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return []
    
    def parse_mrz(self, mrz_lines: list) -> Optional[Dict]:
        """
        Parse MRZ lines and extract passport information
        TD3 format (passport): 2 lines of 44 characters each
        """
        try:
            if len(mrz_lines) < 2:
                logger.error("Insufficient MRZ lines for parsing")
                return None
            
            # Identify which line is line1 (name line) and line2 (passport data line)
            # Line 1 typically starts with 'P' or 'C' (for P< document type)
            # Line 2 typically starts with digits (passport number)
            line1 = None
            line2 = None
            
            for line in mrz_lines[:4]:  # Check first 4 lines max
                if len(line) >= 40:
                    # Line 1: starts with letter (P, C, I, A, V, etc.)
                    if line[0].isalpha() and line1 is None:
                        line1 = line.ljust(44, '<')[:44]
                    # Line 2: contains many digits (passport, DOB, expiry)
                    elif sum(c.isdigit() for c in line) > 10 and line2 is None:
                        line2 = line.ljust(44, '<')[:44]
            
            if not line1 or not line2:
                logger.warning("Could not identify MRZ line1 and line2")
                # Fallback: use first 2 lines
                line1 = mrz_lines[0].ljust(44, '<')[:44]
                line2 = mrz_lines[1].ljust(44, '<')[:44]
            
            logger.info(f"Using Line1: {line1}")
            logger.info(f"Using Line2: {line2}")
            
            # Parse Line 1: P<NATION<<SURNAME<<GIVEN_NAMES<<<<<<<<<<<<<<<
            document_type = line1[0]  # P for passport
            country_code = line1[2:5].replace('<', '')
            
            # Extract names - Format: SURNAME<<GIVEN_NAMES<<<<<<
            # Replace single < with empty, keep << as separator
            names_part = line1[5:44]
            # Split by << to get [SURNAME, GIVEN_NAMES, empty strings...]
            name_parts = [part for part in names_part.split('<<') if part and part != '<']
            surname = name_parts[0] if len(name_parts) > 0 else ''
            given_names = name_parts[1] if len(name_parts) > 1 else ''
            
            # Full name: Surname Given (e.g., YAINAMCHAN PUMMIN)
            full_name = f"{surname} {given_names}".strip()
            
            # Check if name extraction failed (empty or placeholder)
            if not full_name or full_name == '' or surname == '' or line1.startswith('P<XXX'):
                logger.warning("Name extraction failed from Line 1 - name field will be empty, user must enter manually")
                full_name = ''  # Explicitly set to empty string
                surname = ''
                given_names = ''
            
            # Parse Line 2: PASSPORT_NO<CHECK<NATION<DOB<CHECK<SEX<EXPIRY<CHECK<PERSONAL_NO<CHECK<
            passport_number = line2[0:9].replace('<', '').strip()
            passport_check = line2[9]
            nationality = line2[10:13].replace('<', '')
            dob = line2[13:19]  # YYMMDD
            dob_check = line2[19]
            sex = line2[20]
            expiry = line2[21:27]  # YYMMDD
            expiry_check = line2[27]
            personal_number = line2[28:42].replace('<', '').strip()
            final_check = line2[43]
            
            # Validate checksums
            is_valid = self._validate_checksums(line2, passport_number, dob, expiry)
            
            # Format dates
            dob_formatted = self._format_date(dob)
            expiry_formatted = self._format_date(expiry)
            
            result = {
                'document_type': 'Passport' if document_type == 'P' else document_type,
                'country_code': country_code,
                'country_name': self.COUNTRY_CODES.get(country_code, country_code),
                'surname': surname,
                'given_names': given_names,
                'full_name': full_name,
                'passport_number': passport_number,
                'nationality': nationality,
                'nationality_name': self.COUNTRY_CODES.get(nationality, nationality),
                'date_of_birth': dob_formatted,
                'sex': sex,  # Keep as 'M' or 'F' for frontend compatibility
                'sex_full': 'Male' if sex == 'M' else 'Female' if sex == 'F' else 'Other',  # Human-readable version
                'expiry_date': expiry_formatted,
                'personal_number': personal_number,
                'mrz_valid': is_valid,
                'raw_mrz': {
                    'line1': line1,
                    'line2': line2
                }
            }
            
            # Mask passport number in logs
            masked_passport = self._mask_passport(passport_number)
            logger.info(f"Parsed MRZ successfully - Passport: {masked_passport}, Name: {result['full_name']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing MRZ: {e}")
            return None
    
    def _validate_checksums(self, line2: str, passport_no: str, dob: str, expiry: str) -> bool:
        """Validate MRZ checksums"""
        try:
            def check_digit(data: str, check: str) -> bool:
                weights = [7, 3, 1]
                total = 0
                for i, char in enumerate(data):
                    if char == '<':
                        value = 0
                    elif char.isdigit():
                        value = int(char)
                    else:
                        value = ord(char) - ord('A') + 10
                    total += value * weights[i % 3]
                return str(total % 10) == check
            
            # Check passport number
            passport_valid = check_digit(passport_no, line2[9])
            
            # Check date of birth
            dob_valid = check_digit(dob, line2[19])
            
            # Check expiry date
            expiry_valid = check_digit(expiry, line2[27])
            
            return passport_valid and dob_valid and expiry_valid
            
        except Exception as e:
            logger.warning(f"Checksum validation failed: {e}")
            return False
    
    def _format_date(self, date_str: str) -> str:
        """Convert YYMMDD to YYYY-MM-DD"""
        try:
            if len(date_str) != 6:
                return date_str
            
            yy = int(date_str[0:2])
            mm = date_str[2:4]
            dd = date_str[4:6]
            
            # Determine century (assume 1900-2099)
            current_year = datetime.now().year % 100
            if yy <= current_year + 20:
                yyyy = 2000 + yy
            else:
                yyyy = 1900 + yy
            
            return f"{yyyy}-{mm}-{dd}"
            
        except Exception:
            return date_str
    
    def _mask_passport(self, passport_number: str) -> str:
        """Mask passport number for logging (PDPA compliance)"""
        if len(passport_number) <= 4:
            return '*' * len(passport_number)
        return '*' * (len(passport_number) - 4) + passport_number[-4:]
    
    def full_page_text_extract(self, image: np.ndarray) -> Optional[Dict]:
        """
        Primary method: Full page OCR with intelligent text extraction
        Simulates iPhone Text Scanner - reads ALL text from passport page
        """
        try:
            logger.info("🔍 Attempting Full Page Text Extraction (iPhone Text Scanner method)")
            
            # Preprocess image for better OCR
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # Apply preprocessing to improve text clarity
            # 1. Denoise
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # 2. Enhance contrast with CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            
            # 3. Sharpen
            kernel = np.array([[-1,-1,-1],
                              [-1, 9,-1],
                              [-1,-1,-1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)
            
            # Run full page OCR with detailed output
            logger.info("Running full-page OCR...")
            config = '-l eng --oem 3 --psm 3'  # PSM 3 = Fully automatic page segmentation
            text = pytesseract.image_to_string(sharpened, config=config)
            
            logger.info(f"📄 Extracted {len(text)} characters from passport page")
            
            # Parse the extracted text
            data = self._parse_passport_text(text)
            
            if data and (data.get('passport_number') or data.get('full_name')):
                logger.info(f"✅ Full page extraction successful - found {len([k for k,v in data.items() if v])} fields")
                data['method'] = 'full_page_ocr'
                data['extraction_confidence'] = 'high' if data.get('passport_number') and data.get('full_name') else 'medium'
                return data
            else:
                logger.warning("Full page OCR found insufficient data")
                return None
                
        except Exception as e:
            logger.error(f"Full page OCR failed: {e}")
            return None

    def _parse_passport_text(self, text: str) -> Dict:
        """
        Parse extracted text and find passport information
        Similar to iPhone Live Text parsing
        """
        data = {
            'full_name': '',
            'passport_number': '',
            'nationality': '',
            'date_of_birth': '',
            'expiry_date': '',
            'sex': '',
            'mrz_valid': False
        }
        
        # Patterns for extracting data (flexible matching)
        patterns = {
            # Passport Number (various formats)
            'passport': [
                r'(?:passport\s*no\.?|no\.?\s*de\s*passeport|passport\s*number)[:\s]*([A-Z]{1,2}[0-9]{6,8})',
                r'(?:^|\s)([A-Z]{2}[0-9]{7})(?:\s|$)',  # Common format: AB1234567
                r'(?:^|\s)([A-Z][0-9]{8})(?:\s|$)',      # Format: A12345678
            ],
            
            # Surname (after various labels)
            'surname': [
                r'(?:surname|nom)[:\s]*([A-Z][A-Z\s\-\']+?)(?=\s*$|\s*given|\s*prénom)',
                r'(?:name|nom)[:\s]*([A-Z][A-Z\s\-\']+?)(?=\s*$|\s*given)',
            ],
            
            # Given Names
            'given_names': [
                r'(?:given\s*names?|prénoms?)[:\s]*([A-Z][A-Z\s\-\']+?)(?=\s*$|\s*national|\s*sex)',
            ],
            
            # Nationality (3-letter code or full name)
            'nationality': [
                r'(?:nationality|nationalité|code)[:\s]*([A-Z]{3})',
                r'(?:nationality|nationalité)[:\s]*(THAI(?:LAND)?)',
            ],
            
            # Date of Birth (various formats)
            'dob': [
                r'(?:date\s*of\s*birth|birth\s*date|date\s*de\s*naissance)[:\s]*(\d{1,2}[\s\-/](?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JANV|FÉVR|MARS|AVR|MAI|JUIN|JUIL|AOÛT|SEPT)[A-Z]*[\s\-/]\d{4})',
                r'(?:date\s*of\s*birth|birth\s*date)[:\s]*(\d{1,2}[\s\-/]\d{1,2}[\s\-/]\d{4})',
            ],
            
            # Sex/Gender
            'sex': [
                r'(?:sex|sexe|gender)[:\s]*([MFmf])',
            ],
            
            # Expiry Date
            'expiry': [
                r'(?:date\s*of\s*expiry|expiry\s*date|date\s*d[\'\"]expiration|valid\s*until)[:\s]*(\d{1,2}[\s\-/](?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JANV|FÉVR|MARS|AVR|MAI|JUIN|JUIL|AOÛT|SEPT)[A-Z]*[\s\-/]\d{4})',
                r'(?:date\s*of\s*expiry|expiry)[:\s]*(\d{1,2}[\s\-/]\d{1,2}[\s\-/]\d{4})',
            ],
        }
        
        # Extract each field
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    
                    # Process based on field type
                    if field == 'passport':
                        data['passport_number'] = value.upper().replace(' ', '')
                        logger.info(f"Found passport number: {self._mask_passport(value)}")
                        break
                        
                    elif field == 'surname':
                        data['surname'] = value.title()
                        logger.info(f"Found surname: {value}")
                        break
                        
                    elif field == 'given_names':
                        data['given_names'] = value.title()
                        logger.info(f"Found given names: {value}")
                        break
                        
                    elif field == 'nationality':
                        nat = value.upper()
                        if nat in ['THAILAND', 'THAI']:
                            nat = 'THA'
                        data['nationality'] = nat
                        logger.info(f"Found nationality: {nat}")
                        break
                        
                    elif field == 'dob':
                        parsed_date = self._parse_date_string(value)
                        if parsed_date:
                            data['date_of_birth'] = parsed_date
                            logger.info(f"Found DOB: {parsed_date}")
                        break
                        
                    elif field == 'sex':
                        data['sex'] = value.upper()
                        logger.info(f"Found sex: {value.upper()}")
                        break
                        
                    elif field == 'expiry':
                        parsed_date = self._parse_date_string(value)
                        if parsed_date:
                            data['expiry_date'] = parsed_date
                            logger.info(f"Found expiry: {parsed_date}")
                        break
        
        # Combine surname and given names
        if data.get('surname') or data.get('given_names'):
            parts = []
            if data.get('surname'):
                parts.append(data['surname'])
            if data.get('given_names'):
                parts.append(data['given_names'])
            data['full_name'] = ', '.join(parts)
            logger.info(f"Combined full name: {data['full_name']}")
        
        # Add sex_full for compatibility
        if data['sex']:
            data['sex_full'] = 'Male' if data['sex'] == 'M' else 'Female' if data['sex'] == 'F' else ''
        
        return data

    def _parse_date_string(self, date_str: str) -> Optional[str]:
        """
        Parse various date formats to YYYY-MM-DD
        Handles: "09 AUG 1997", "09/08/1997", "09-08-1997", etc.
        """
        month_map = {
            'JAN': '01', 'JANV': '01',
            'FEB': '02', 'FÉV': '02', 'FÉVR': '02', 'FEVR': '02',
            'MAR': '03', 'MARS': '03',
            'APR': '04', 'AVR': '04',
            'MAY': '05', 'MAI': '05',
            'JUN': '06', 'JUIN': '06',
            'JUL': '07', 'JUIL': '07',
            'AUG': '08', 'AOU': '08', 'AOÛT': '08', 'AOUT': '08',
            'SEP': '09', 'SEPT': '09',
            'OCT': '10',
            'NOV': '11',
            'DEC': '12', 'DÉC': '12'
        }
        
        # Try month name format: "09 AUG 1997"
        match = re.search(r'(\d{1,2})[\s\-/]([A-ZÀ-ÿ]+)[\s\-/](\d{4})', date_str, re.IGNORECASE)
        if match:
            day = match.group(1).zfill(2)
            month_str = match.group(2).upper()
            year = match.group(3)
            
            # Find matching month
            for key, value in month_map.items():
                if month_str.startswith(key) or key.startswith(month_str[:3]):
                    return f"{year}-{value}-{day}"
        
        # Try numeric format: "09/08/1997" or "09-08-1997"
        match = re.search(r'(\d{1,2})[\s\-/](\d{1,2})[\s\-/](\d{4})', date_str)
        if match:
            day = match.group(1).zfill(2)
            month = match.group(2).zfill(2)
            year = match.group(3)
            return f"{year}-{month}-{day}"
        
        return None
    
    def fallback_ocr(self, image: np.ndarray) -> Optional[Dict]:
        """
        Legacy fallback method - kept for compatibility
        Use full_page_text_extract() instead
        """
        return self.full_page_text_extract(image)
    
    def process_passport(self, image_path: str, debug_save: bool = False) -> Dict:
        """
        Main processing pipeline:
        1. Try Full Page Text Extraction (iPhone Text Scanner method) FIRST
        2. Fall back to MRZ OCR if full page fails
        
        Args:
            image_path: Path to passport image
            debug_save: If True, saves preprocessed images for debugging
        """
        import os
        debug_save = True  # Always save debug images
        
        try:
            logger.info(f"Processing passport image: {os.path.basename(image_path)}")
            
            # Load original image
            original_img = cv2.imread(image_path)
            if original_img is None:
                return {'success': False, 'error': 'Cannot read image file'}
            
            orig_height, orig_width = original_img.shape[:2]
            logger.info(f"Original image size: {orig_width}x{orig_height}")
            
            debug_dir = os.path.join(tempfile.gettempdir(), 'mrz_debug')
            os.makedirs(debug_dir, exist_ok=True)
            
            # ============================================
            # STEP 1: Try Full Page Text Extraction FIRST
            # ============================================
            logger.info("=" * 60)
            logger.info("STEP 1: Attempting Full Page Text Extraction (Primary)")
            logger.info("=" * 60)
            
            full_page_data = self.full_page_text_extract(original_img)
            
            if full_page_data and full_page_data.get('passport_number'):
                # Success with full page extraction
                logger.info("✅ SUCCESS with Full Page Text Extraction!")
                
                # Add warnings if needed
                if not full_page_data.get('full_name'):
                    full_page_data['name_missing'] = True
                    full_page_data['name_warning_message'] = 'Name could not be read. Please enter Full Name manually.'
                
                return {
                    'success': True,
                    'method': 'full_page_text',
                    'data': full_page_data
                }
            
            # ============================================
            # STEP 2: Fallback to MRZ OCR
            # ============================================
            logger.info("=" * 60)
            logger.info("STEP 2: Full page failed, falling back to MRZ OCR")
            logger.info("=" * 60)
            
            # Step 1: Extract MRZ region from HIGH-RES original image
            # This preserves maximum detail for OCR
            logger.info("Extracting MRZ from HIGH-RES original image...")
            orig_gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
            
            # Extract bottom 20% to ensure we capture BOTH MRZ lines
            # Line 1 (P<THA + name) can be higher up in the MRZ zone
            mrz_high_res = orig_gray[int(orig_height * 0.80):orig_height, :]
            logger.info(f"High-res MRZ region size: {mrz_high_res.shape[1]}x{mrz_high_res.shape[0]}")
            
            # Save high-res MRZ
            if debug_save:
                highres_path = os.path.join(debug_dir, f"{os.path.basename(image_path)}_1_highres_mrz.jpg")
                cv2.imwrite(highres_path, mrz_high_res)
                logger.info(f"💾 Debug: High-res MRZ saved to {highres_path}")
            
            # Step 2: Preprocess ONLY the MRZ region (not the whole image)
            processed_mrz = self._preprocess_mrz_only(mrz_high_res)
            
            if debug_save:
                processed_path = os.path.join(debug_dir, f"{os.path.basename(image_path)}_2_processed_mrz.jpg")
                cv2.imwrite(processed_path, processed_mrz)
                logger.info(f"💾 Debug: Processed MRZ saved to {processed_path}")
                logger.info(f"🔍 Check these images in: {debug_dir}")
            
            # Step 3: Try COMPLETELY RAW first (no preprocessing at all)
            logger.info("Trying COMPLETELY RAW OCR (no preprocessing)...")
            raw_lines = self.ocr_mrz(mrz_high_res)
            
            if len(raw_lines) >= 2:
                logger.info(f"✅ Success with COMPLETELY RAW OCR!")
                mrz_lines = raw_lines
            elif len(raw_lines) == 1:
                # Special case: Single line with valid country code and MRZ pattern (Line 2)
                line2_candidate = raw_lines[0]
                has_country = any(line2_candidate[i:i+3] in self.COUNTRY_CODES for i in range(len(line2_candidate)-2))
                digit_count = sum(c.isdigit() for c in line2_candidate[:25])
                
                if has_country and digit_count >= 12:
                    logger.info(f"✅ Detected MRZ Line 2: {line2_candidate}")
                    logger.info(f"   Looking for Line 1 in upper region...")
                    
                    # Try to find Line 1 by scanning ABOVE the Line 2 region
                    # Line 1 is typically 100-150 pixels above Line 2
                    h = mrz_high_res.shape[0]
                    
                    # Extract upper portion of MRZ (where Line 1 should be)
                    line1_region = mrz_high_res[0:int(h*0.6), :]  # Top 60% of MRZ region
                    
                    # Try OCR on Line 1 region
                    line1_candidates = []
                    config_simple = f'-l eng --oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ<0123456789'
                    try:
                        text = pytesseract.image_to_string(line1_region, config=config_simple)
                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                        for line in lines:
                            cleaned = ''.join(c for c in line if c.isalnum() or c == '<')
                            # CRITICAL: Validate Line 1 format
                            # Must start with P< or similar document type indicator
                            # OR must contain valid country code (since OCR might misread P<)
                            if len(cleaned) >= 30:  # Reduced from 35 to 30 to catch truncated OCR
                                is_valid = False
                                
                                # Method 1: Starts with valid document type (P, I, A, C, V)
                                if cleaned[0] in 'PIACV' and (len(cleaned) < 2 or cleaned[1] in '<PIACV'):
                                    country_part = cleaned[2:5] if len(cleaned) > 4 else ''
                                    if country_part in self.COUNTRY_CODES or '<' in country_part:
                                        is_valid = True
                                        logger.info(f"✅ Valid Line 1 (starts with doc type): {cleaned[:50]}")
                                
                                # Method 2: Contains valid country code anywhere (OCR might misread P<)
                                if not is_valid:
                                    for i in range(len(cleaned) - 2):
                                        if cleaned[i:i+3] in self.COUNTRY_CODES:
                                            # Found country code - likely Line 1 with misread prefix
                                            # BUT: Need to check it's NOT Line 2 (which also has country code)
                                            # Line 1 = P<COUNTRY<<NAME<<< (mostly letters)
                                            # Line 2 = PASSPORT#<COUNTRY<DOB<SEX<EXPIRY (mostly digits)
                                            
                                            letter_count = sum(c.isalpha() for c in cleaned)
                                            digit_count = sum(c.isdigit() for c in cleaned)
                                            
                                            # Line 1: letters >> digits (names have lots of letters)
                                            # Line 2: digits >> letters (passport#, dates have lots of digits)
                                            if letter_count >= 15 and letter_count > digit_count:
                                                is_valid = True
                                                logger.info(f"✅ Valid Line 1 (has country '{cleaned[i:i+3]}', {letter_count} letters, {digit_count} digits): {cleaned[:50]}")
                                            else:
                                                logger.warning(f"Rejected (looks like Line 2: {digit_count} digits > {letter_count} letters): {cleaned[:40]}")
                                            break
                                
                                if is_valid:
                                    line1_candidates.append(cleaned)
                                else:
                                    logger.warning(f"Rejected Line 1 (no valid markers): {cleaned[:30]}")
                    except Exception as e:
                        logger.warning(f"Line 1 OCR failed: {e}")
                    
                    if line1_candidates:
                        line1 = line1_candidates[0]
                        logger.info(f"✅ Found valid Line 1: {line1[:50]}")
                        mrz_lines = [line1, line2_candidate]
                    else:
                        logger.warning("Could not find valid Line 1 - will try extracting name from Line 2 or use empty placeholder")
                        # Use a more obvious placeholder that the parsing code can detect
                        mrz_lines = ['P<XXX<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<', line2_candidate]
                else:
                    logger.info(f"Single line from raw OCR lacks valid pattern - trying preprocessed...")
                    mrz_lines = []
            else:
                # Step 4: If raw fails, try preprocessed
                logger.info("Raw failed, trying preprocessed OCR...")
                mrz_lines = self.ocr_mrz(processed_mrz)
                
                # Check preprocessed result for single line too
                if len(mrz_lines) == 1:
                    line = mrz_lines[0]
                    has_country = any(line[i:i+3] in self.COUNTRY_CODES for i in range(len(line)-2))
                    digit_count = sum(c.isdigit() for c in line[:25])
                    
                    if has_country and digit_count >= 12:
                        logger.info(f"✅ Single line detected with valid country code (PREPROCESSED)")
                        logger.info(f"   Treating as MRZ Line 2: {line}")
                        mrz_lines = ['P<XXX<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<', line]
            
            # If still no success, try different crop positions
            # Maybe MRZ is in a different location
            if len(mrz_lines) < 2:
                logger.info("Trying different crop positions...")
                crop_positions = [
                    (0.85, "Bottom 15%"),
                    (0.75, "Bottom 25%"),
                    (0.88, "Bottom 12%"),
                ]
                
                for crop_start, desc in crop_positions:
                    logger.info(f"Trying {desc} crop...")
                    alt_mrz = orig_gray[int(orig_height * crop_start):orig_height, :]
                    
                    if debug_save:
                        alt_path = os.path.join(debug_dir, f"{os.path.basename(image_path)}_4_alt_{int(crop_start*100)}.jpg")
                        cv2.imwrite(alt_path, alt_mrz)
                    
                    # Try raw first
                    alt_lines = self.ocr_mrz(alt_mrz)
                    if len(alt_lines) >= 2:
                        logger.info(f"✅ Success with {desc} crop!")
                        mrz_lines = alt_lines
                        break
                    
                    # Try preprocessed
                    alt_processed = self._preprocess_mrz_only(alt_mrz)
                    alt_lines = self.ocr_mrz(alt_processed)
                    if len(alt_lines) >= 2:
                        logger.info(f"✅ Success with {desc} crop (preprocessed)!")
                        mrz_lines = alt_lines
                        break
            
            # If extraction failed, try with the RAW grayscale image (no preprocessing)
            if len(mrz_lines) < 2:
                logger.info("Trying RAW grayscale OCR without preprocessing...")
                # Load original image and convert to grayscale only
                raw_img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if raw_img is not None:
                    # Extract MRZ from raw image - BOTTOM 15-18% only
                    h, w = raw_img.shape[:2]
                    raw_mrz = raw_img[int(h * 0.82):h, :]
                    
                    if debug_save:
                        raw_path = os.path.join(debug_dir, f"{os.path.basename(image_path)}_3_raw_mrz.jpg")
                        cv2.imwrite(raw_path, raw_mrz)
                        logger.info(f"💾 Debug: Raw MRZ saved to {raw_path}")
                    
                    raw_lines = self.ocr_mrz(raw_mrz)
                    if len(raw_lines) >= 2:
                        logger.info(f"✅ Success with RAW grayscale OCR!")
                        mrz_lines = raw_lines
            
            # Special case: If we got only 1 line with valid country code and MRZ pattern,
            # treat it as Line 2 (passport data line) and proceed
            if len(mrz_lines) == 1:
                line = mrz_lines[0]
                # Check if it looks like MRZ Line 2 (has country code and lots of digits)
                has_country = any(line[i:i+3] in self.COUNTRY_CODES for i in range(len(line)-2))
                digit_count = sum(c.isdigit() for c in line[:25])
                
                if has_country and digit_count >= 12:
                    logger.info(f"✅ Single line detected with valid country code and MRZ pattern")
                    logger.info(f"   Treating as MRZ Line 2 (passport data): {line}")
                    # Create dummy Line 1 and use this as Line 2
                    mrz_lines = ['P<XXX<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<', line]
                else:
                    logger.warning(f"Single line without valid MRZ pattern: {line[:50]}")
            
            # If still failed, try rotating the original high-res grayscale and retry
            if len(mrz_lines) < 2:
                logger.warning(f"Initial extraction failed ({len(mrz_lines)} lines). Trying rotations...")
                
                # Try 90, 180, 270 degree rotations on original grayscale
                for angle in [90, 180, 270]:
                    logger.info(f"Trying {angle}° rotation...")
                    (h, w) = orig_gray.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    
                    # Calculate new dimensions to fit rotated image
                    cos = np.abs(M[0, 0])
                    sin = np.abs(M[0, 1])
                    new_w = int((h * sin) + (w * cos))
                    new_h = int((h * cos) + (w * sin))
                    
                    # Adjust transformation matrix for new dimensions
                    M[0, 2] += (new_w / 2) - center[0]
                    M[1, 2] += (new_h / 2) - center[1]
                    
                    rotated = cv2.warpAffine(orig_gray, M, (new_w, new_h), 
                                            flags=cv2.INTER_CUBIC,
                                            borderMode=cv2.BORDER_REPLICATE)
                    
                    # Extract MRZ from rotated and preprocess
                    rot_h, rot_w = rotated.shape[:2]
                    rotated_mrz = rotated[int(rot_h * 0.82):rot_h, :]
                    rotated_processed = self._preprocess_mrz_only(rotated_mrz)
                    
                    rotated_lines = self.ocr_mrz(rotated_processed)
                    if len(rotated_lines) >= 2:
                        logger.info(f"✅ Success with {angle}° rotation!")
                        mrz_lines = rotated_lines
                        break
            
            # Check MRZ quality
            if len(mrz_lines) < 1:
                logger.warning(f"Poor quality: No MRZ lines detected")
                
                if debug_save:
                    logger.error(f"❌ EXTRACTION FAILED - Check debug images in: {debug_dir}")
                    logger.error(f"   1. Preprocessed full image: {os.path.basename(image_path)}_1_preprocessed.jpg")
                    logger.error(f"   2. Extracted MRZ region: {os.path.basename(image_path)}_2_mrz_region.jpg")
                
                # Provide specific guidance based on what we found
                tips = [
                    '📸 <strong>Use good lighting</strong> - avoid shadows on MRZ area',
                    '🎯 <strong>IMPORTANT: Focus ONLY on the MRZ</strong> (2 lines at bottom)',
                    '📐 <strong>Take photo straight-on</strong>, not at an angle',
                    '📏 <strong>Get VERY close</strong> - MRZ text must be large and clear',
                    '🔍 <strong>Zoom in on just the bottom section</strong> with the 2 text lines',
                    '✉️ <strong>Best method: Email/Google Drive</strong> (NOT Line - it compresses images)',
                ]
                
                # Check if we got any text at all
                if debug_save:
                    tips.insert(0, '🔍 <strong>DEBUG MODE:</strong> Check saved images in temp folder')
                
                return {
                    'success': False,
                    'error': 'Cannot read MRZ text - Image quality too low or wrong area photographed',
                    'error_code': 'LOW_QUALITY',
                    'suggestion': {
                        'title': '❌ MRZ Not Detected - Please Try Again',
                        'tips': tips,
                        'mrz_info': '<strong>CRITICAL:</strong> You must photograph ONLY the bottom 2 lines of text (MRZ = Machine Readable Zone). The MRZ looks like: P&lt;THAXXX...  and  XX123456&lt;7THA... Get as close as possible so these 2 lines fill the photo!'
                    }
                }
            
            # Step 4: Parse MRZ
            if len(mrz_lines) >= 2:
                # Validate the lines before parsing - reject obvious garbage
                line1 = mrz_lines[0]
                line2 = mrz_lines[1] if len(mrz_lines) > 1 else ""
                
                # IMPORTANT: OCR might read lines in wrong order
                # Check if we need to swap line1 and line2
                # Line 1 should start with 'P' and have country code
                # Line 2 should have passport number (alphanumeric at start)
                
                swap_needed = False
                if not line1.startswith('P') and line2.startswith('P'):
                    logger.info("Lines appear to be reversed - swapping...")
                    line1, line2 = line2, line1
                    swap_needed = True
                elif not line1.startswith('P'):
                    # Check if line1 looks like Line 2 (starts with passport number)
                    # Line 2 typically: PASSPORT_NO + CHECK + COUNTRY + DOB + etc
                    # Look for pattern: some letters/digits followed by 3-letter country code
                    for i in range(len(line1) - 3):
                        three_chars = line1[i:i+3]
                        if three_chars in self.COUNTRY_CODES:
                            logger.info(f"Found country code '{three_chars}' in line1 at pos {i}")
                            logger.info("Line1 appears to be MRZ Line 2 - looking for Line 1...")
                            # Try to find Line 1 in remaining lines
                            for j in range(1, min(len(mrz_lines), 10)):
                                if mrz_lines[j].startswith('P'):
                                    logger.info(f"Found Line 1 at position {j} - swapping")
                                    line1, line2 = mrz_lines[j], line1
                                    swap_needed = True
                                    break
                            break
                
                # Basic sanity checks
                is_valid = True
                error_reasons = []
                
                # Line 1 should start with 'P' for passport (after any swap)
                if not line1.startswith('P'):
                    is_valid = False
                    error_reasons.append(f"Line 1 doesn't start with 'P' (got: '{line1[:10]}')")
                
                # Check for too many consecutive identical characters (suggests garbage)
                for line in [line1, line2]:
                    for i in range(len(line) - 5):
                        if len(set(line[i:i+6])) == 1:  # 6 identical chars in a row
                            is_valid = False
                            error_reasons.append(f"Too many identical chars: '{line[i:i+6]}'")
                            break
                
                # Check for reasonable character distribution
                alpha_count = sum(c.isalpha() for c in line1 + line2)
                digit_count = sum(c.isdigit() for c in line1 + line2)
                bracket_count = (line1 + line2).count('<')
                total = len(line1) + len(line2)
                
                # Relaxed validation for poor OCR
                if alpha_count < total * 0.15:  # At least 15% letters
                    is_valid = False
                    error_reasons.append(f"Too few letters: {alpha_count}/{total}")
                
                if digit_count < total * 0.05:  # At least 5% digits (very lenient)
                    is_valid = False
                    error_reasons.append(f"Too few digits: {digit_count}/{total}")
                
                # If we found a country code, be more lenient
                has_country_code = any(line1[i:i+3] in self.COUNTRY_CODES for i in range(len(line1)-2))
                has_country_code = has_country_code or any(line2[i:i+3] in self.COUNTRY_CODES for i in range(len(line2)-2))
                
                if has_country_code:
                    logger.info("Found valid country code - relaxing validation")
                    is_valid = True  # Override validation if we found country code
                    error_reasons = []
                
                if not is_valid:
                    logger.warning(f"MRZ validation failed: {'; '.join(error_reasons)}")
                    logger.warning(f"Line 1: {line1}")
                    logger.warning(f"Line 2: {line2}")
                    
                    if debug_save:
                        logger.error(f"❌ GARBAGE OUTPUT DETECTED - Check debug images in: {debug_dir}")
                    
                    return {
                        'success': False,
                        'error': 'OCR produced invalid output - image quality too poor',
                        'error_code': 'INVALID_MRZ',
                        'debug_info': {
                            'line1': line1,
                            'line2': line2,
                            'validation_errors': error_reasons,
                            'debug_dir': debug_dir if debug_save else None
                        },
                        'suggestion': {
                            'title': '❌ Cannot Read Passport - OCR Validation Failed',
                            'tips': [
                                '📸 <strong>Image too blurry or low quality</strong>',
                                '🔍 <strong>Take a NEW photo focusing ONLY on the MRZ lines</strong>',
                                '💡 <strong>Ensure VERY good lighting - no shadows</strong>',
                                '📐 <strong>Hold phone steady and get close</strong>',
                                '✉️ <strong>Email the image (NOT Line - it compresses)</strong>',
                                '🖼️ <strong>Try scanning with a scanner instead of camera</strong>',
                            ],
                            'mrz_info': f'<strong>DEBUG:</strong> Check processed images at: {debug_dir if debug_save else "N/A"}'
                        }
                    }
                
                passport_data = self.parse_mrz(mrz_lines)
                
                if passport_data:
                    # Check if name was not extracted
                    if not passport_data.get('full_name') or passport_data.get('full_name').strip() == '':
                        logger.warning("Name could not be extracted from MRZ - user must enter manually")
                        passport_data['name_missing'] = True
                        passport_data['name_warning_message'] = 'Name could not be read. Please enter Full Name manually.'
                    
                    # Check if data looks reasonable
                    passport_num = passport_data.get('passport_number', '')
                    if len(passport_num) < 6 or not any(c.isdigit() for c in passport_num):
                        logger.warning(f"Suspicious passport number: {passport_num}")
                        passport_data['quality_warning'] = True
                        passport_data['warning_message'] = 'Data quality low - please verify all fields carefully'
                    
                    # Accept data even if checksum fails (common with photos)
                    # But add warning flag for user review
                    if not passport_data.get('mrz_valid'):
                        passport_data['checksum_warning'] = True
                        logger.warning(f"MRZ checksum validation failed but data extracted - requires user review")
                    
                    return {
                        'success': True,
                        'method': 'mrz',
                        'data': passport_data
                    }
            
            # Step 5: Fallback to full OCR
            logger.warning("MRZ parsing failed, trying fallback OCR")
            fallback_data = self.fallback_ocr(original_img)
            
            if fallback_data and fallback_data.get('passport_number'):
                return {
                    'success': True,
                    'method': 'fallback',
                    'data': fallback_data,
                    'warning': 'Data extracted via fallback method, please verify manually'
                }
            
            return {
                'success': False,
                'error': 'Could not extract passport information'
            }
            
        except Exception as e:
            logger.error(f"Error processing passport: {e}")
            return {
                'success': False,
                'error': str(e)
            }


def convert_pdf_to_images(pdf_path: str) -> list:
    """
    Convert PDF to images
    Returns list of temporary image paths
    """
    try:
        from pdf2image import convert_from_path
        
        logger.info(f"Converting PDF to images: {pdf_path}")
        
        # Convert PDF pages to images
        images = convert_from_path(pdf_path, dpi=300)
        
        # Save to temp files
        temp_paths = []
        for i, image in enumerate(images):
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=f'_page{i}.jpg'
            )
            image.save(temp_file.name, 'JPEG')
            temp_paths.append(temp_file.name)
            temp_file.close()
        
        logger.info(f"Converted {len(temp_paths)} pages from PDF")
        return temp_paths
        
    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")
        return []


def cleanup_temp_files(file_paths: list):
    """Delete temporary files (PDPA compliance)"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted temp file: {os.path.basename(file_path)}")
        except Exception as e:
            logger.warning(f"Could not delete {file_path}: {e}")
