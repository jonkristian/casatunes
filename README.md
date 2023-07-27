# CasaTunes

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[CasaTunes](https://www.casatunes.com/) is a Multi-Room audio system. With CasaTunes, you can pick and choose from our flexible line of music servers and matrix amplifiers to create the perfect multiroom audio solution for your customers, whether looking for an entry, value, or high performance solution.

## Installation

### Installation via Home Assistant Community Store (HACS)
1. Ensure [HACS](http://hacs.xyz/) is installed.
2. Add this repo url to custom repositories in HACS.
3. Install and restart Home Assistant
3. If CasaTunes isn't detected after restart you should be able to add it via the integrations screen.

### Manual installation
Download or clone and copy the folder `custom/components/casatunes` into your `custom_components/`

## Discovery
Your casatunes unit should be discovered automatically, if this doesn't happen, please go to integrations and add it manually with the ip address of your unit.

## Attributions
- [alphasixtyfive] for the first casatunes component.
- This component uses the excellent [integration_blueprint] from [ludeeus].

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

⭐️ this repository if you found it useful ❤️

[![BuyMeCoffee][buymecoffebadge2]][buymecoffee]

[casatunes]: https://github.com/jonkristian/casatunes
[buymecoffee]: https://www.buymeacoffee.com/jonkristian
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[buymecoffebadge2]: https://bmc-cdn.nyc3.digitaloceanspaces.com/BMC-button-images/custom_images/white_img.png
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/jonkristian/casatunes.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Jon%20Kristian%20Nilsen%20%40jonkristian-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/jonkristian/casatunes.svg?style=for-the-badge
[releases]: https://github.com/jonkristian/casatunes/releases
[exampleimg]: example.png
[integration_blueprint]: https://github.com/ludeeus/integration_blueprint
[ludeeus]: https://github.com/ludeeus/
[alphasixtyfive]: https://github.com/alphasixtyfive/