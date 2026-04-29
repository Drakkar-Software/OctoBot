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

$(document).ready(function() {
    const fetchDSLKeywordsIfPossible = async () => {
        const dslTableBody = $("#dsl-keywords-table-body");
        if(dslTableBody.length === 0 || dslTableBody.length === 0){
            return;
        }
        const url = dslTableBody.data("update-url");
        const response = await async_send_and_interpret_bot_update(undefined, url, null, "GET");
        response.forEach(keywordData => {
            dslTableBody.append(`<tr><td>${keywordData.name}</td><td>${keywordData.description}</td><td>${keywordData.example}</td><td>${keywordData.type}</td></tr>`);
        });
        $("#dsl-keywords-table").DataTable({
            "pageLength": 50,
            "order": [[ 3, "desc" ], [ 0, "asc" ]],
        });
    }
    fetchDSLKeywordsIfPossible();
});