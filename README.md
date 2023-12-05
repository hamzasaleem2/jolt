# Jolt - JSON-Based Zapier-like Automation

Jolt is a Python console application that facilitates automation through customizable triggers and actions defined in JSON files, known as "recipes". It provides a lightweight alternative to Zapier, empowering users to automate tasks.

## Features

- **Custom Triggers and Actions:**
  Define your triggers and actions using a simple JSON file.

- **Multiple Actions per Trigger:**
  Integrate multiple triggers and actions, enabling complex workflows.

- **Extensibility:**
  You can easily expand Jolt’s capabilities by creating new projects and linking them to triggers and actions.

- **Filtering Mechanism:**
  Use a flexible filtering system to conditionally execute actions based on specified criteria.

- **Logging:**
  All functions and triggers are placed in the `recipe_logs` file for reference and debugging purposes.

## Example Usage

Here is an example of a JSON recipe that demonstrates the versatility of Jolt:

```json
{
  "trigger": "airtable_record_updated",
  "actions": [
    {
      "type": "send_webhook",
      "webhook_url": "",
      "filters": [],
      "output_name": "first_action_output"
    },
    {
      "type": "send_webhook",
      "webhook_url": "",
      "filters": []
    },
    {
      "type": "send_webhook",
      "webhook_url": "",
      "filters": [],
      "input_from": ["first_action_output"]
    }
  ],
  "filters": [
    {
      "field_name": "Name",
      "operator": "contains",
      "value": "sa"
    }
  ],
  "base_key": "",
  "table_name": "",
  "api_key": "",
  "field_name": null,
  "text_to_find": null,
  "name": "newupdate"
}

