/*
 * Drakkar-Software OctoBot
 * Copyright (c) Drakkar-Software, All rights reserved.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3.0 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.
 */

// set bootstrap 4 theme for JSONEditor (https://github.com/json-editor/json-editor#css-integration)
JSONEditor.defaults.options.iconlib = 'fontawesome5';
// custom octobot theme
class OctoBotTheme extends JSONEditor.defaults.themes.bootstrap4 {
  getButton(text, icon, title) {
    const el = super.getButton(text, icon, title);
    el.classList.remove("btn-secondary");
    el.classList.add("btn-sm", "btn-primary", "waves-effect", "px-2", "px-md-4");
    return el;
  }
  getCheckbox() {
    const el = this.getFormInputField('checkbox');
    el.classList.add("custom-control-input");
    return el;
  }
  getCheckboxLabel(text) {
    const el = this.getFormInputLabel(text);
    el.classList.add("custom-control-label");
    return el;
  }
  getFormControl(label, input, description) {
    const group = document.createElement("div");

    if (label && input.type === "checkbox") {
      group.classList.add("checkbox", "custom-control", "custom-switch");
      group.appendChild(input);
      group.appendChild(label);
    } else {
      group.classList.add("form-group");
      if (label) {
        label.classList.add("form-control-label");
        group.appendChild(label);
      }
      group.appendChild(input);
    }

    if (description) group.appendChild(description);

    return group;
  }
  getIndentedPanel () {
    const el = document.createElement('div')
    el.classList.add('card', 'card-body', 'mb-3', "px-1", "px-md-3")

    if (this.options.object_background) {
      el.classList.add(this.options.object_background)
    }

    if (this.options.object_text) {
      el.classList.add(this.options.object_text)
    }

    /* for better twbs card styling we should be able to return a nested div */

    return el
  }
}


// custom delete confirm prompt
class ConfirmArray extends JSONEditor.defaults.editors.array {
  askConfirmation() {
    if (this.jsoneditor.options.prompt_before_delete === true) {
      if (confirm("Remove this element ?") === false) {
        return false;
      }
    }
    return true;
  }
}

JSONEditor.defaults.themes.octobot = OctoBotTheme;
JSONEditor.defaults.editors.array = ConfirmArray;
JSONEditor.defaults.options.theme = 'octobot';
JSONEditor.defaults.options.required_by_default = true;
