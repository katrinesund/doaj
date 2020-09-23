$.extend(doaj, {
    af: {
        state : {
            context: false,
            currentTab: 0,
            previousTab: 0,
            tabs: false,
            sections: false
        },

        init: (params) => {
            doaj.af.state.currentTab = params.hasOwnProperty("currentTab") ? params.currentTab : 0;
            doaj.af.state.previousTab = params.hasOwnProperty("previousTab") ? params.previousTab : 0;

            $("input, select").each((idx, inp) => {
                let name = $(inp).attr("name").split("-");
                $(inp).attr("data-parsley-errors-container", "#" + name[0] + "_checkbox-errors")
            });

            $("#reviewed").on("click", doaj.af.manage_review_checkboxes);

            doaj.af.state.context = $(".application_form").attr("context");
            doaj.af.state.tabs = $(".tab");
            doaj.af.state.sections = $(".form-section");

            doaj.af.prepareSections();
            doaj.af.usePaginationMenu();
             // Display the current tab
            if (doaj.af.state.context === "admin") {
                setup_maned();
            }
            // $(".application_form").parsley().validate();
            doaj.af.state.currentTab = -1;
            for (let i = 0; i < doaj.af.state.tabs.length; i++) {
                next();
                // showTab(i);
            }
            doaj.af.state.currentTab = 0;
            showTab(doaj.af.state.currentTab);
        },

        showTab: (n) => {
            // This function will display the specified tab of the form ...
            //hide all other tabs
            if (n < sections.length-1){
                let hiddenField = $("#validated-" + n);
                if (hiddenField.val() === "") {
                    hiddenField.val("False");
                }
            }

            tabs.each((idx, tab) => {
                $(tab).hide();
            });

            let submitButton = $("#submitBtn");
            let draftButton = $("#draftBtn");
            $(tabs[n]).show();
            $("#cannot_save_draft").hide();
            submitButton.hide();
            draftButton.show();
            // ... and fix the Previous/Next buttons:
            if (n === 0) {
                $("#prevBtn").hide();
            } else {
                $("#prevBtn").show();
            }

            if (n === (tabs.length - 1)) {
                //show submit button only if all tabs are validated
                $("#nextBtn").hide();
                submitButton.hide();
                draftButton.show();
                let validated = form_validated();
                if (!validated) {
                    $("#cannot-submit-invalid-fields").show();
                } else {
                    $("#cannot-submit-invalid-fields").hide();
                }

            } else {
                let nextBtn = $("#nextBtn");
                nextBtn.show();
                nextBtn.html("Next");
                submitButton.hide();
                draftButton.show();
            }
            currentTab = n;
            previousTab = n-1;
            // ... and run a function that displays the correct step indicator:
            if(n === 6) {
                $("#validated-6").val("True");
                prepareReview()
            }
            if (context === "admin") {
                modify_view();
            }
            else if (context === "public") {
                fixStepIndicator(n)
            }
            window.scrollTo(0,0);
        },

        prepareReview: () => {
            let review_values = $("td[id$='__review_value']");
            review_values.each((idx, question) => {
                let id = $(question).attr('id');
                // TODO: think about how to generalise this.  If we add more fields like this or
                // change the apc_charges bit then it will need updating
                if (id === "apc_charges__review_value") {
                    let currency = $("select[id$='apc_currency']");
                    let max = $("input[id$='apc_max']");
                    let result = "";
                    let isValid = true;
                    for (let i = 0; i < currency.length; i++){
                        let curr = $(currency[i]).find('option:selected').text();
                        let m = $(max[i]).val();
                        if (m !== "" || curr !== "") {
                            result += (m === "" ? "" : m) + " " + (curr === "" ? "" : curr) + " " + "<br>";
                        }
                    }
                    if ($(max[0]).parsley().validationResult !== true || ($(currency[0]).parsley().validationResult !== true)) {
                        isValid = false;
                    }
                    if (result === "" && isValid){
                        $(question).parent().hide();
                    }
                    else {
                        $(question).parent().show();
                        $(question).html(result);
                    }
                }
                else {
                    let name = id.substring(0, id.indexOf("__review_value"));
                    let input = $("input[name^='" + name + "']");
                    if (input.length === 0) {  //it's not input but select
                        input = $("[name^='" + name + "']");
                        let result = "";
                        input.each((idx, inp) => {
                            let val = $(inp).find('option:selected').text();
                            if (val !== "") {
                                result += val + "<br>";
                            }

                        })
                        $(question).html(result);
                    } else {
                        if (id === "keywords__review_value") {
                            let result = "";
                            let this_input = $('#keywords')
                            let keywords = this_input.val().split(",")
                            if (keywords.length !== 1) {
                                $(keywords).each((idx, kw) => {
                                    result += kw + "<br>";
                                });
                            }
                            else {
                                result = keywords[0];
                            }
                            $(question).html(result);


                        } else {
                            if ($(input).attr("data-parsley-required-if") !== undefined) {
                                if (input.val() === "" && $(input).parsley().validationResult === true){
                                    $(question).parent().hide();
                                    return;
                                }
                                else {
                                    $(question).parent().show();
                                }
                            }
                            let type = input.attr("type");
                            if (type === "text" || type === "number") {
                                $(question).html(input.val())
                            } else if (type === "url") {
                                $(question).html('<a href=' + input.val() + '>' + input.val() + '</a>')
                            } else if (type === "radio") {
                                if (input.is(":checked")) {
                                    let text = $('label[for=' + $(input.filter(':checked')).attr('id') + ']').text();
                                    $(question).html(text);
                                }
                            } else if (type === "checkbox") {
                                let result = ''
                                input.each((idx, i) => {
                                    if ($(i).is(":checked")) {
                                        let text = $('label[for=' + $(i).attr('id') + ']').text();
                                        result += text + "<br>";
                                    }
                                })
                                $(question).html(result)
                            }
                        }
                    }
                }

            })
        },

        form_validated: () => {
            let result = true;
            let inputs = $("[name^='validated']");
            $(inputs).each((idx, input) => {
                if (idx === inputs.length-1) {
                    return result;
                }
                if ($(input).val() !== "True") {
                    result = false;
                    return;
                }
            });
            return result;
        },

        next: () => {
            navigate(currentTab + 1);
        },

        prev: () => {
            navigate(currentTab - 1, true);
        },

        submitaplication: () => {
            let form = $("form");
            let parsleyForm = $(form).parsley();
            $(form).submit();
        },

        savedraft: () => {
            let form = $(".application_form");
            $(form).attr('novalidate', 'novalidate');
            var draftEl = $("input[name=draft]");
            if (draftEl.length === 0) {
                let input = $("<input>")
                   .attr("type", "hidden")
                   .attr("name", "draft").val(true);
                form.append($(input));
            } else {
                draftEl.val(true);
            }

            let parsleyForm = $(form).parsley();
            parsleyForm.destroy();
            $(form).submit();
        },

        navigate: (n, showEvenIfInvalid = false) => {
            // Hide the current tab:
            var form = $('#' + '{{ form_id }}');
            form.parsley().whenValidate({
                group: 'block-' + currentTab
            }).done(function () {
                $("#validated-" + currentTab).val("True");
                previousTab = n-1;
                currentTab = n;
                // Otherwise, display the correct tab:
                showTab(currentTab);
            }).fail(function () {
                $("#validated-" + currentTab).val("False");
                if (showEvenIfInvalid){
                    previousTab = n-1;
                    currentTab = n;
                    // Otherwise, display the correct tab:
                    showTab(currentTab);
                }

            });
        },

        fixStepIndicator: (n) => {
            // This function removes the "active" class of all steps...
            $(".application-nav__list-item").each((idx, x) => {
                let hiddenField = $("#validated-" + idx);
                if (idx === n) {
                    x.className = "application-nav__list-item application-nav__list-item--active";
                }
                else {
                    if (hiddenField.val() === "True") {
                        x.className = "application-nav__list-item application-nav__list-item--done";
                    } else if (hiddenField.val() === "False") {
                        x.className = "application-nav__list-item application-nav__list-item--invalid";
                    }
                    else {
                        x.className = "application-nav__list-item";
                    }
                }
            });
            //... and adds the "active" class to the current step:

            $("#page_link-" + n).className = "page_link";
        },

        usePaginationMenu: () => {
            $('[id^="page_link-"]').each((i, x) => {
                $(x).on("click", () => {
                    if (context === "public" && $("#validated-" + i).val() === '') {
                        //dev only!
                        //navigate(i);
                        return false;
                    } else {
                        navigate(i, true);
                    }

                });
            });
        },

        prepareSections: () => {
            sections.each((idx, section) => {

                $(section).find("input, select").each((i, input) => {
                    $(input).attr('data-parsley-group', 'block-' + idx);
                });

                if (idx < sections.length){
                    let hiddenInputs = $("[name='validated']");
                    $(hiddenInputs[idx]).attr('id', 'validated-' + idx);
                }

            });

            $('[id^="page_link-"]').each((i, menu) =>  {
                $(menu).className = "page_link--disabled";
            });
        },

        manage_review_checkboxes: () => {
            if ($("#reviewed").checked) {
                form_validated() ? $("#submitBtn").show() : $("#submitBtn").hide()
            }

        }
    }
});

window.Parsley.addValidator("requiredIf", {
    validateString : function(value, requirement, parsleyInstance) {
        let field = parsleyInstance.$element.attr("data-parsley-required-if-field");
        if ($('[name="' + field + '"]').filter(':checked').val() === requirement){
            return !!value;
        }
        return true;
    },
    messages: {
        en: 'This field is required, because you answered "%s" to the previous question.'
    },
    priority: 33
});

window.Parsley.addValidator("requiredvalue", {
    validateString : function(value, requirement) {
        return (value === requirement);
    },
    messages: {
        en: 'DOAJ only indexed open access journals which comply with the statement above. Please check and update the open access statement of your journal. You may return to this application at any time.'
    },
    priority: 32
});

window.Parsley.addValidator("optionalIf", {
    validateString : function(value, requirement) {
        theOtherField = $("[name = " + requirement + "]");
        if (!!value || !!($(theOtherField)).val()) {
            $(theOtherField).parsley().reset();
            return true;
        }
        return false;
    },
    messages: {
        en: 'You need to provide the answer to either this field or %s field (or both)'
    },
    priority: 300
});

window.Parsley.addValidator("differentTo", {
    validateString : function(value, requirement) {
      return (!value || ($("[name = " + requirement + "]")).val() !== value)
    },
    messages: {
        en: 'Value of this field and %s field must be different'
    },
    priority: 1
});