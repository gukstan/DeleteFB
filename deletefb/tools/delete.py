from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from .common import SELENIUM_EXCEPTIONS, click_button, wait_xpath, force_mobile
from .config import settings

import time

# Used as a threshold to avoid running forever
MAX_POSTS = settings["MAX_POSTS"]

def delete_posts(driver, user_profile_url, year=None):
    """
    Deletes posts from the wall by moving them to trash.

    Args:
        driver: seleniumrequests.Chrome Driver instance
        user_profile_url: str
        year: optional int YYYY year
    """

    if year is not None:
        user_profile_url = "{0}/timeline?year={1}".format(user_profile_url, year)

    user_profile_url = force_mobile(user_profile_url)
    driver.get(user_profile_url)

    for _ in range(MAX_POSTS):
        try:
            # Find the ellipsis menu button for the first post and click it
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@aria-label, 'Actions for this post')]"))
            )
            ellipsis_button = driver.find_element(By.XPATH, "//div[contains(@aria-label, 'Actions for this post')]")
            ellipsis_button.click()

            # Try to find and click "Move to Trash"
            try:
                # Wait for "Move to Trash" option to be visible and click it
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.XPATH, "//span[contains(text(), 'Move to trash')]"))
                )
                move_to_trash_button = driver.find_element(By.XPATH, "//span[contains(text(), 'Move to trash')]")
                move_to_trash_button.click()

                move_button_xpath = "//div[div[div[span[span[contains(text(), 'Move')]]]]]"
                move_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, move_button_xpath))
                )
                move_button.click()
                print("Post moved to trash.")
            except (TimeoutException, NoSuchElementException):
                try:
                    delete_post_button = driver.find_element(By.XPATH, "//span[contains(text(), 'Delete post')]")
                    delete_post_button.click()

                    delete_xpath = "//div[div[div[span[span[contains(text(), 'Delete')]]]]]"
                    delete_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, delete_xpath))
                    )
                    delete_button.click()
                    print("Delete Post.")
                except:
                    # If "Move to Trash" not found, try "Remove Tag"
                    remove_tag = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Remove tag')]"))
                    )
                    remove_tag.click()
                    print("Tag removed.")

            # Add delay for the action to complete
            time.sleep(2)

        except (NoSuchElementException, TimeoutException) as e:
            print("Could not find the post or 'Move to Trash' option: ", e)
            break  # Exit the loop if no more posts are found or unable to delete

        # Refresh the page to load new set of posts
        driver.refresh()

    print("Finished deleting posts.")