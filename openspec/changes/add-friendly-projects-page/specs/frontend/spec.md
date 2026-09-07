## ADDED Requirements

### Requirement: Friendly projects navigation

The frontend SHALL expose a Russian-language `Проекты` navigation item that
opens the friendly projects page. On desktop, the item SHALL be visually
separated from the four primary navigation sections and SHALL appear before the
theme controls. On mobile, it SHALL remain available in the navigation drawer.

#### Scenario: Desktop visitor opens the projects page

- **WHEN** a desktop visitor selects `Проекты` in the header
- **THEN** the application navigates to the friendly projects page
- **AND** the navigation item remains visually distinct from the four primary sections and the theme controls

#### Scenario: Mobile visitor opens the projects page

- **WHEN** a mobile visitor opens the navigation drawer
- **THEN** the drawer includes a `Проекты` destination

### Requirement: Friendly projects directory

The frontend SHALL present a responsive `Дружественные проекты` page containing
clear Russian and Esperanto descriptions and links for Biologio and Frazaro.
Each external link SHALL identify its destination and SHALL open safely in a new
browser tab.

#### Scenario: Visitor reviews friendly projects

- **WHEN** a visitor opens the friendly projects page
- **THEN** Biologio and Frazaro are presented as separate, readable entries
- **AND** each entry includes Russian and Esperanto descriptions and its destination address

#### Scenario: Visitor follows a project link

- **WHEN** a visitor follows either external project link
- **THEN** the destination opens in a new browser tab without exposing the opener context
