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
JSONEditor.defaults.themes.octobot = JSONEditor.defaults.themes.bootstrap4.extend({
  getButton: function(text, icon, title) {
    var el = this._super(text, icon, title);
    el.classList.remove("btn-secondary");
    el.classList.add("btn-sm", "btn-primary", "waves-effect");
    return el;
  }
});

// custom delete confirm prompt
JSONEditor.defaults.editors.array = JSONEditor.defaults.editors.array.extend({
  askConfirmation: function() {
    if (this.jsoneditor.options.prompt_before_delete === true) {
      if (confirm("Remove this element ?") === false) {
        return false;
      }
    }
    return true;
  }
});

JSONEditor.defaults.options.theme = 'octobot';
