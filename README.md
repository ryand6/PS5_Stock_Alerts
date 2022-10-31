# PS5_Stock_Alerts

PS5 Stock Alerts Python script that automates checking availability of PS5 consoles across major UK retailers.

When available stock is found, the link to the product page is sent by email to the intended recipient identified in the script.

Whilst the script is running, it creates a log file (if it doesn't already exist) to keep track of each check and to record errors to help with debugging if the
script isn't working as intended.

A csv file is also created to keep an inventory of the products that have been monitored, keeping track of their current availability status and the last time each
specific product has been checked.

PLEASE NOTE: this is for educational purposes and should not be used in any way that violates the TOS set by any of the websites accessed in the script.
