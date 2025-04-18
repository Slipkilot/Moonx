import unittest
import time
import re
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from appium.options.android import UiAutomator2Options
from selenium.common.exceptions import NoSuchElementException

# --- Capabilities ---
capabilities = {
    'platformName': 'Android',
    'automationName': 'UiAutomator2',
    'platformVersion': '14.0',
    'deviceName': 'emulator-5554',
    'app': 'C:/Users/ahmet/moonx/build/app/outputs/apk/debug/app-debug.apk',
    'noReset': False,
    'unicodeKeyboard': True,
    'resetKeyboard': True
}
APPIUM_SERVER_URL = 'http://localhost:4723'

# --- Helper Functions ---
def swipe_on_element(driver, element, direction="up", duration=400, vertical_offset_ratio=0.3):
    try:
        location = element.location; size = element.size
        center_x = location['x'] + size['width'] / 2; center_y = location['y'] + size['height'] / 2
        swipe_distance = size['height'] * vertical_offset_ratio
        start_y = center_y
        if direction == "up": end_y = center_y - swipe_distance
        elif direction == "down": end_y = center_y + swipe_distance
        else: end_y = center_y - swipe_distance
        driver.swipe(center_x, start_y, center_x, end_y, duration)
    except Exception as e:
        print(f"   !! Swipe sırasında hata: {e}") 

def extract_number(desc):
    if desc is None: return None
    match = re.search(r'\d+', desc)
    return int(match.group(0)) if match else None

def set_wheel_value_adaptively(driver, wheel_element, target_value_str, max_swipes=40, value_type="numeric", months_list=None):
    for i in range(max_swipes):
        current_value_str = wheel_element.get_attribute('content-desc')
        if current_value_str is None: time.sleep(0.5); current_value_str = wheel_element.get_attribute('content-desc')
        if current_value_str is None: unittest.TestCase().fail("Tekerlek değeri okunamıyor.")
        diff = 0; match = False

        if value_type == "numeric":
            current_value_int = extract_number(current_value_str)
            target_value_int = int(target_value_str)
            if current_value_int is None: unittest.TestCase().fail(f"Tekerlekten sayı okunamadı: '{current_value_str}'")
            if current_value_int == target_value_int: match = True
            diff = current_value_int - target_value_int
        elif value_type == "month":
            if months_list is None: raise ValueError("Aylar listesi gerekli ('month')")
            current_val_lower = current_value_str.lower(); target_val_lower = target_value_str.lower()
            if current_val_lower == target_val_lower: match = True
            try:
                current_index = [m.lower() for m in months_list].index(current_val_lower)
                target_index = [m.lower() for m in months_list].index(target_val_lower)
                diff = current_index - target_index
            except ValueError: diff = -1
        elif value_type == "ampm":
            if current_value_str.upper() == target_value_str.upper(): match = True
            diff = 1 if current_value_str.upper() == "PM" and target_value_str.upper() == "AM" else -1
        else: raise ValueError("Invalid value_type for set_wheel_value")

        if match: return True
        if diff == 0: return True

        if value_type == "numeric" or value_type == "month":
             if abs(diff) >= 10: ratio = 0.4
             elif abs(diff) >= 5: ratio = 0.3
             elif abs(diff) == 4: ratio = 0.25
             elif abs(diff) == 3: ratio = 0.2
             elif abs(diff) == 2: ratio = 0.15
             else: ratio = 0.1
        elif value_type == "ampm": ratio = 0.2

        if diff > 0: swipe_on_element(driver, wheel_element, "down", vertical_offset_ratio=ratio)
        else: swipe_on_element(driver, wheel_element, "up", vertical_offset_ratio=ratio)
        time.sleep(0.8)
    else: 
        last_value = wheel_element.get_attribute('content-desc')
        print(f"Ayarlanamadı ({target_value_str})! Maksimum denemeye ({max_swipes}) ulaşıldı. Son değer: {last_value}") 
        return False

# --- Test Class ---
class MoonxOnboardingRefactoredTest(unittest.TestCase):

    driver = None
    implicitly_wait_time = 15
    short_wait = 1
    medium_wait = 2 
    long_wait = 4  

    @classmethod
    def setUpClass(cls):
        print("Test Başlıyor: Appium sürücüsü oluşturuluyor...") 
        try:
            cls.driver = webdriver.Remote(command_executor=APPIUM_SERVER_URL, options=UiAutomator2Options().load_capabilities(capabilities))
            cls.driver.implicitly_wait(cls.implicitly_wait_time)
            print("Sürücü başarıyla oluşturuldu."); time.sleep(cls.long_wait+2); print("Uygulama açıldı.") 
        except Exception as e: print(f"HATA: Sürücü başlatılamadı! {e}"); raise

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'driver') and cls.driver: print("Test Bitti: Sürücü kapatılıyor..."); cls.driver.quit(); print("Sürücü kapatıldı.") 

    # --- Action Helper Methods ---
    def _find_element(self, by, value, description):
        try:
            element = self.driver.find_element(by=by, value=value)
            return element
        except NoSuchElementException:
            self.fail(f"'{description}' elementi bulunamadı! Locator: {by}='{value}'")
        except Exception as e:
            self.fail(f"'{description}' elementi aranırken beklenmedik hata! Locator: {by}='{value}'. Hata: {e}")

    def _click_element(self, by, value, description, wait_after=short_wait):
        element = self._find_element(by, value, description)
        try:
            element.click()
            if wait_after > 0: time.sleep(wait_after)
        except Exception as e:
            self.fail(f"'{description}' elementine tıklanırken hata oluştu: {e}")

    def _set_date(self, target_year, target_month_en, target_day):
        birth_date_xpath = "(//android.widget.ImageView[contains(@content-desc, 'Enter Birth Date')]/android.widget.Button)[1]"
        self._click_element(AppiumBy.XPATH, birth_date_xpath, "Doğum Tarihi Seçici Aç", wait_after=self.long_wait)

        year_xpath = "//android.widget.SeekBar[@index='4']"; month_xpath = "//android.widget.SeekBar[@index='2']"; day_xpath = "//android.widget.SeekBar[@index='3']"; done_button_id = "Done"
        year_wheel = self._find_element(AppiumBy.XPATH, year_xpath, "Yıl Tekerleği"); month_wheel = self._find_element(AppiumBy.XPATH, month_xpath, "Ay Tekerleği"); day_wheel = self._find_element(AppiumBy.XPATH, day_xpath, "Gün Tekerleği")

        months_in_picker = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        if not set_wheel_value_adaptively(self.driver, year_wheel, target_year, value_type="numeric"): self.fail("Yıl ayarlanamadı.")
        if not set_wheel_value_adaptively(self.driver, month_wheel, target_month_en, value_type="month", months_list=months_in_picker): self.fail("Ay ayarlanamadı.")
        if not set_wheel_value_adaptively(self.driver, day_wheel, target_day, value_type="numeric"): self.fail("Gün ayarlanamadı.")

        self._click_element(AppiumBy.ACCESSIBILITY_ID, done_button_id, "Tarih Seçici Done", wait_after=self.medium_wait)

    def _set_time(self, target_hour, target_minute, target_ampm):
        birth_time_xpath = "(//android.widget.ImageView[contains(@content-desc, 'Enter Birth Time')]/android.widget.Button)[2]"
        self._click_element(AppiumBy.XPATH, birth_time_xpath, "Doğum Saati Seçici Aç", wait_after=self.long_wait)

        hour_xpath = "//android.widget.SeekBar[@index='0']"; minute_xpath = "//android.widget.SeekBar[@index='1']"; ampm_xpath = "//android.widget.SeekBar[@index='2']"
        hour_wheel = self._find_element(AppiumBy.XPATH, hour_xpath, "Saat Tekerleği"); minute_wheel = self._find_element(AppiumBy.XPATH, minute_xpath, "Dakika Tekerleği"); ampm_wheel = self._find_element(AppiumBy.XPATH, ampm_xpath, "AM/PM Tekerleği")

        if not set_wheel_value_adaptively(self.driver, hour_wheel, target_hour, value_type="numeric"): self.fail("Saat ayarlanamadı.")
        if not set_wheel_value_adaptively(self.driver, minute_wheel, target_minute, max_swipes=60, value_type="numeric"): self.fail("Dakika ayarlanamadı.")
        if not set_wheel_value_adaptively(self.driver, ampm_wheel, target_ampm, max_swipes=5, value_type="ampm"): self.fail("AM/PM ayarlanamadı.")

        screen_size = self.driver.get_window_size(); tap_x = screen_size['width'] * 0.5; tap_y = screen_size['height'] * 0.1
        self.driver.tap([(int(tap_x), int(tap_y))]);
        time.sleep(self.medium_wait)

    def _set_birth_place(self, target_city):
        birth_place_selector_id = "Select Birth Place"
        self._click_element(AppiumBy.ACCESSIBILITY_ID, birth_place_selector_id, "Doğum Yeri Seçici Aç", wait_after=self.long_wait)

        city_wheel_xpath = "//android.widget.SeekBar[@index='2']"; city_picker_done_button_id = "Done"
        city_wheel = self._find_element(AppiumBy.XPATH, city_wheel_xpath, "Şehir Tekerleği")

        max_city_swipes = 15
        for i in range(max_city_swipes):
            current_city = city_wheel.get_attribute('content-desc')
            if current_city.lower() == target_city.lower(): print(f"  Hedef Şehir '{target_city}' Ayarlandı!"); break
            swipe_on_element(self.driver, city_wheel, "up", vertical_offset_ratio=0.2)
            time.sleep(0.8)
        else: 
            self.fail(f"Doğum yeri ayarlanamadı ({target_city})! Maksimum denemeye ulaşıldı. Son değer: {city_wheel.get_attribute('content-desc')}")

        self._click_element(AppiumBy.ACCESSIBILITY_ID, city_picker_done_button_id, "Doğum Yeri Seçici Done", wait_after=self.medium_wait)

    def _handle_permission(self):
        permission_button_id = "com.android.permissioncontroller:id/permission_allow_foreground_only_button"
        time.sleep(2) 
        self._click_element(AppiumBy.ID, permission_button_id, "İzin Ver (While using app)", wait_after=self.medium_wait)

    def _verify_horoscope(self, expected_sign):
        print(f"\nAlt Adım: Burç Doğrulama (Beklenen: {expected_sign})...") 
        time.sleep(self.long_wait)
        extracted_sign = None
        try:
            horoscope_sign_xpath_guess = f"//*[contains(@text, '{expected_sign}') or contains(@content-desc, '{expected_sign}')]"
            horoscope_element = self._find_element(AppiumBy.XPATH, horoscope_sign_xpath_guess, f"{expected_sign} Burcu Metni")
            sign_text = horoscope_element.text; sign_desc = horoscope_element.get_attribute('content-desc')

            if sign_desc and expected_sign.lower() in sign_desc.lower(): extracted_sign = sign_desc.split()[0]
            elif sign_text and expected_sign.lower() in sign_text.lower(): extracted_sign = sign_text.split()[0]
            else: extracted_sign = sign_desc if sign_desc else sign_text

            if extracted_sign is None: self.fail("Burç metni elementten alınamadı.")
            self.assertEqual(expected_sign.lower(), extracted_sign.lower().strip(),
                             f"HATA: Beklenen burç '{expected_sign}', bulunan '{extracted_sign}'")
            print(f"Doğrulama Başarılı: Ekranda '{extracted_sign}' burcu görünüyor.") 

        except Exception as e:
             print(f"HATA: Burç kontrolü sırasında: {e}")
             raise e

    # --- Main Test Flow ---
    def test_full_onboarding_flow(self):
        print("\n--- Test Başlıyor: Tam Onboarding Akışı ---") 
        try:
            self._click_element(AppiumBy.ACCESSIBILITY_ID, 'Next', "Welcome Next")
            self._set_date(target_year="1996", target_month_en="August", target_day="01")
            self._set_time(target_hour="11", target_minute="05", target_ampm="AM")
            self._click_element(AppiumBy.ACCESSIBILITY_ID, 'Next', "Doğum Tarihi/Saati Next")
            self._set_birth_place(target_city="Chittagong")
            self._click_element(AppiumBy.ACCESSIBILITY_ID, 'Next', "Doğum Yeri Final Next")
            self._handle_permission()
            self._verify_horoscope(expected_sign="Leo")

            print("\n--- Test Başarıyla Tamamlandı ---") 

        except Exception as e:
            print(f"\n!!!!!!!!!!!!!!!! HATA !!!!!!!!!!!!!!!!!!!!") 
            print(f"Test akışı sırasında bir hata oluştu: {e}")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
            page_source_mesaji = "Sayfa kaynağı alınamadı."
            try:
                print("\n--- SAYFA KAYNAĞI (HATA ANINDA) ---") 
                page_source_mesaji = self.driver.page_source
                print(page_source_mesaji)
                print("-----------------------------------\n")
            except Exception as pe:
                print(f"Sayfa kaynağı alınamadı: {pe}")
            self.fail(f"Test akışı sırasında hata oluştu: {e}")


# --- Run Tests ---
if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(MoonxOnboardingRefactoredTest)
    unittest.TextTestRunner(verbosity=1).run(suite) 