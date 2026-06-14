# Tologo Garage Opener Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/JTorkk/tologo-hass.svg)](https://github.com/JTorkk/tologo-hass/releases)
[![License](https://img.shields.io/github/license/JTorkk/tologo-hass.svg)](LICENSE)

A custom integration for Home Assistant to control [Tologo](https://www.tologo.fi/) garage door openers via their cloud API.

## Features

* **Button Control:** Provides a simple push-button entity to trigger your Tologo garage door. 
* **Automatic Discovery:** All associated Tologo doors (and their location metadata) are automatically discovered and added to Home Assistant during the initial setup.
* **Instant UI Feedback:** Button presses complete instantly in the Home Assistant interface, while the actual API call is safely dispatched in the background.
* **Anti-Spam Protection:** Includes a built-in 5-second cooldown per door to prevent accidental rapid-fire presses and API rate limiting.
* **Error Notifications:** If a door fails to open, a persistent notification will automatically alert you directly in the Home Assistant dashboard.
* **UI Configuration:** Easy setup directly from the Home Assistant integrations dashboard (no YAML required).

## Installation

### Option 1: HACS (Recommended)
This is the easiest way to install and keep the integration updated.

1. Open Home Assistant and navigate to **HACS**.
2. Click on **Integrations**.
3. Click the three dots in the top right corner and select **Custom repositories**.
4. Add the URL to this GitHub repository and select **Integration** as the category.
5. Click **Add**, then search for "Tologo Garage Opener" in HACS and click **Download**.
6. Restart Home Assistant.

### Option 2: Manual Installation
1. Download the latest release from the [Releases page](https://github.com/JTorkk/tologo-hass/releases).
2. Extract the zip file and copy the `custom_components/tologo` folder into your Home Assistant `custom_components` directory.
3. Restart Home Assistant.

## Configuration & Discovery

Configuration is handled entirely via the Home Assistant UI. 

### Initial Setup
1. Go to **Settings** > **Devices & Services**.
2. Click the **+ Add Integration** button in the bottom right corner.
3. Search for **Tologo** and select it.
4. Enter your Tologo account **Email** and **Password**. 
5. Once authenticated, all existing doors will be automatically discovered and added as devices in Home Assistant.

### Discovering New Doors
If you get access to a new Tologo door *after* setting up this integration, it will not appear automatically. To discover the newly added door:
1. Go to **Settings** > **Devices & Services**.
2. Find the **Tologo** integration card.
3. Click the three dots (`⋮`) on the integration card and select **Reload**. 
4. The integration will re-sync with Tologo and pull in your new door automatically without dropping your existing configuration.

## Supported Entities

This integration currently provides the following entities:

| Entity Domain | Description |
| ------------- | ----------- |
| `button`      | A stateless button to trigger the door opening mechanism. |

## Debugging and Issues

If you find a bug or have a feature request, please open an issue.

## Legal Disclaimer
This is an unofficial, community-developed integration. This project is not affiliated with, endorsed by, or officially connected to Tolotech Oy or the Tologo brand in any way. All product names, logos, brands, trademarks, and registered trademarks (including but not limited to Tologo) are the property of Tolotech Oy. Their use in this project is strictly for identification purposes only to indicate compatibility with Home Assistant.
This software is provided "as is", without warranty of any kind, express or implied. The developer of this integration assumes no responsibility for any damage to your property, network, or garage door mechanism resulting from the use of this custom integration. Use at your own risk.