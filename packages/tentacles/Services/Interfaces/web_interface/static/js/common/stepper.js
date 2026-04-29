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

function updateProgress(){
    const progress = getCurrentStepId() * 100 / getStepsCount();
    $(".progress-bar").css('width', progress+'%').attr("aria-valuenow", progress);
}

function triggerCallbacksIfAny(stepId){
    if (isDefined(stepperCallbackById && isDefined(stepperCallbackById[stepId]))){
        stepperCallbackById[stepId]();
    }
}

function updateButtonsDisplay(){
    const currentStepId = getCurrentStepId();
    const stepsCount = getStepsCount();
    const previousButton = $("#previous-step");
    const nextButton = $("#next-step");
    if(currentStepId < 2){
        previousButton.addClass("disabled");
    }else{
        previousButton.removeClass("disabled");
    }
    if(currentStepId >= stepsCount){
        nextButton.addClass("disabled");
    }else{
        nextButton.removeClass("disabled");
    }
}

function getStep(stepId){
    return $(`.tutorial-step[data-step-id=${stepId}]`);
}

function getCurrentStep(){
    return $(".tutorial-step").not(".d-none");
}

function getCurrentStepId(){
    return getCurrentStep().data("stepId");
}

function getStepsCount(){
    return $(".tutorial-step").length;
}

function changeStep(next){
    const currentStep = getCurrentStepId();
    const nextStepId = next ? currentStep + 1 : currentStep - 1;
    if(nextStepId > 0 && nextStepId <= getStepsCount()){
        getCurrentStep().addClass(hidden_class);
        getStep(nextStepId).removeClass(hidden_class);
        window.scrollTo(0, 0);
    }
    updateButtonsDisplay();
    updateProgress();
    triggerCallbacksIfAny(getCurrentStepId());
}

function handleStepsButtons(){
    const previousButton = $("#previous-step");
    const nextButton = $("#next-step");
    nextButton.click(function (){
        changeStep(true);
    });
    previousButton.click(function (){
        changeStep(false);
    });
}

$(document).ready(function() {
    updateButtonsDisplay();
    updateProgress();
    handleStepsButtons();
    triggerCallbacksIfAny(getCurrentStepId());
});
