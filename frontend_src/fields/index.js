import { history_initiator_types } from '../history';
import {
    OneHistoryStringFieldMixin,
    OneHistoryFieldMixin,
    HistoryExecutor,
    OneHistoryExecutor,
    OneHistoryChoicesFieldMixin,
    OneHistoryBooleanFieldMixin,
} from './mixins';
import FKJustValueFieldMixin from './FKJustValueFieldMixin.vue';
import OneHistoryRawInventory from './OneHistoryRawInventory.vue';
import SeeAlso from './SeeAlso.vue';
const path_pk_key = spa.utils.path_pk_key;
const guiFields = spa.fields.guiFields;

/**
 * Inventory autocomplete guiField class.
 */
guiFields.inventory_autocomplete = class InventoryAutocompleteField extends spa.fields.fk.multiAutocomplete
    .FKMultiAutocompleteField {
    /**
     * Redefinition of 'toInner' method of fk_multi_autocomplete guiField.
     */
    toInner(data) {
        let val, value;
        val = value = data[this.options.name];

        if (!value) {
            return;
        }

        if (value && typeof value == 'object') {
            val = value.value;
        }

        if (!val) {
            return;
        }

        if (!isNaN(Number(val))) {
            return val;
        }

        if (val[val.length - 1] == ',') {
            return val;
        }

        let prefix = './';

        if (val.substr(0, 2) == prefix) {
            return val;
        }

        return prefix + val;
    }

    /**
     * Method, that defines - make prefetch or not.
     * @param {object} data Instance data.
     * @return {boolean}
     * @private
     */
    _prefetchDataOrNot(data) {
        let value = this.toInner(data);

        if (!isNaN(Number(value))) {
            return true;
        }

        return false;
    }
    /**
     * Redefinition of 'prefetchDataOrNot' method of fk_multi_autocomplete guiField.
     */
    prefetchDataOrNot(data) {
        return this._prefetchDataOrNot(data);
    }
    /**
     * Redefinition of 'makeLinkOrNot' method of fk_multi_autocomplete guiField.
     */
    makeLinkOrNot(data) {
        return this._prefetchDataOrNot(data);
    }
};

/**
 * Playbook autocomplete guiField class.
 */
guiFields.playbook_autocomplete = class PlaybookAutocompleteField extends spa.fields.fk.autocomolete
    .FKAutocompleteField {
    /**
     * Method, that defines - make prefetch or not.
     * @param {object} data Instance data.
     * @return {boolean}
     * @private
     */
    _prefetchDataOrNot(data) {
        /* jshint unused: false */
        return false;
    }
    /**
     * Redefinition of 'prefetchDataOrNot' method of fk_multi_autocomplete guiField.
     */
    prefetchDataOrNot(data) {
        return this._prefetchDataOrNot(data);
    }
    /**
     * Redefinition of 'makeLinkOrNot' method of fk_multi_autocomplete guiField.
     */
    makeLinkOrNot(data) {
        return this._prefetchDataOrNot(data);
    }
};

/**
 * Module autocomplete guiField class.
 */
guiFields.module_autocomplete = class ModuleAutocompleteField extends guiFields.playbook_autocomplete {};

/**
 * Group autocomplete guiField class.
 */
guiFields.group_autocomplete = class GroupAutocompleteField extends guiFields.playbook_autocomplete {};

/**
 * Mixin for classes of fields, that depended on project field value.
 * These fields should format queryset urls containing project id.
 * Project id can be either in instance's data or in route's url params.
 */
const field_depended_on_project_mixin = (Class_name) =>
    class extends Class_name {
        /**
         * Redefinition of 'formatQuerySetUrl' method of fk guiField.
         */
        formatQuerySetUrl(url = '', data = {}, params = {}) {
            /* jshint unused: false */
            if (url.indexOf('{') == -1) {
                return url;
            }

            let project = data.project || app.application.$route.params[path_pk_key];

            if (project && typeof project == 'object' && project.value) {
                project = project.value;
            }

            return url.format({ [path_pk_key]: project });
        }
    };

/**
 * History Mode guiField class.
 */
guiFields.history_mode = class HistoryModeField extends field_depended_on_project_mixin(guiFields.fk) {
    /**
     * Redefinition of 'getPrefetchValue' method of fk guiField.
     */
    getPrefetchValue(data = {}, prefetch_data = {}) {
        return {
            value: prefetch_data[this.options.additionalProperties.value_field],
            prefetch_value: data[this.options.name],
        };
    }
    /**
     * Method returns string with value of instance's 'mode' field (playbook or module).
     * @param data {object} Object with instance data.
     * @return {string}
     */
    getMode(data = {}) {
        return data.kind.toLowerCase();
    }
    /**
     * Method returns true, is instance's 'mode' field value equals to 'playbook', otherwise, returns false.
     * @param data {object} Object with instance data.
     * @return {boolean}
     */
    isPlaybookMode(data = {}) {
        return this.getMode(data) === 'playbook';
    }
    /**
     * Redefinition of 'getPrefetchFilterName' method of fk guiField.
     */
    getPrefetchFilterName(data = {}) {
        return this.isPlaybookMode(data) ? 'pb_filter' : 'name';
    }
    /**
     * Redefinition of 'isPrefetchDataForMe' method of fk guiField.
     */
    isPrefetchDataForMe(data = {}, prefetch_data = {}) {
        let field_name = this.isPlaybookMode(data) ? 'playbook' : 'name';

        return data[this.options.name] == prefetch_data[field_name];
    }
    /**
     * Redefinition of 'getAppropriateQuerySet' method of fk guiField.
     */
    getAppropriateQuerySet(data = {}, querysets = null) {
        let qs = querysets || this.options.additionalProperties.querysets;

        return qs.filter((item) => item.url.indexOf(this.getMode(data)) !== -1)[0];
    }
};

/**
 * One History Mode guiField class.
 */
guiFields.one_history_mode = class OneHistoryModeField extends guiFields.history_mode {
    static get mixins() {
        return super.mixins.concat(OneHistoryStringFieldMixin, {
            mixins: [OneHistoryFieldMixin],
        });
    }
};

/**
 * History Initiator guiField class.
 */
guiFields.history_initiator = class HistoryInitiatorField extends field_depended_on_project_mixin(
    guiFields.fk,
) {
    static get initiatorTypes() {
        return history_initiator_types;
    }
    /**
     * Redefinition of 'getAppropriateQuerySet' method of fk guiField.
     */
    getAppropriateQuerySet(data = {}, querysets = null) {
        let qs = querysets;

        if (!qs) {
            qs = this.options.additionalProperties.querysets;
        }

        let dict = this.constructor.initiatorTypes;

        let selected = qs[0];

        let path = dict[data.initiator_type];

        if (!path) {
            return selected;
        }

        for (let index = 0; index < qs.length; index++) {
            let item = qs[index];

            let p1 = item.url.replace(/^\/|\/$/g, '').split('/');
            let p2 = path.replace(/^\/|\/$/g, '').split('/');

            if (p1.last == p2.last) {
                selected = item;
            }
        }

        return selected;
    }
};

/**
 * OneHistory Initiator guiField class.
 */
guiFields.one_history_initiator = class OneHistoryInitiatorField extends guiFields.history_initiator {
    static get mixins() {
        return super.mixins.concat(OneHistoryStringFieldMixin, {
            mixins: [OneHistoryFieldMixin],
        });
    }
};

/**
 * History Executor guiField class.
 */
guiFields.history_executor = class HistoryExecutorField extends guiFields.fk {
    /**
     * Redefinition of 'makeLinkOrNot' method of fk guiField.
     * @param {object} data
     */
    makeLinkOrNot(data = {}) {
        if (data.initiator_type == 'scheduler') {
            return false;
        }

        return true;
    }
    /**
     * Redefinition of 'prefetchDataOrNot' method of fk guiField.
     * @param {object} data
     */
    prefetchDataOrNot(data = {}) {
        if (data.initiator_type == 'scheduler') {
            return false;
        }

        return true;
    }
    /**
     * Redefinition of 'toRepresent' method of fk guiField.
     * @param {object} data
     */
    toRepresent(data = {}) {
        if (data.initiator_type == 'scheduler') {
            return 'system';
        }

        let value = data[this.options.name];

        if (value && typeof value == 'object') {
            return value.prefetch_value;
        }

        return value;
    }

    static get mixins() {
        return super.mixins.concat(HistoryExecutor);
    }
};

/**
 * OneHistory Executor guiField class.
 */
guiFields.one_history_executor = class OneHistoryExecutorField extends guiFields.history_executor {
    static get mixins() {
        return super.mixins.concat(OneHistoryStringFieldMixin, OneHistoryExecutor);
    }
};

class AnsibleJsonMapper extends spa.fields.json.JsonMapper {
    getComponent(value, name = undefined) {
        if (name === 'seealso') {
            return SeeAlso;
        }
        return super.getComponent(value, name);
    }
}

/**
 * Ansible json guiField class.
 */
guiFields.ansible_json = class AnsibleJsonField extends spa.fields.json.JSONField {
    constructor(options = {}) {
        super(options, new AnsibleJsonMapper());
    }
};

/**
 * FK field class, that always shows only 'field_content_readonly' component - value string (with link).
 * This field does not show label, description and other components.
 * This field is supposed to be used in views for OneHistory model.
 */
guiFields.fk_just_value = class FkJustValueField extends spa.fields.fk.fk.FKField {
    static get mixins() {
        return super.mixins.concat(FKJustValueFieldMixin);
    }
};

/**
 * History String guiField class.
 * String field for views for OneHistory model.
 */
guiFields.one_history_string = class OneHistoryStringField extends spa.fields.text.StringField {
    static get mixins() {
        return super.mixins.concat(OneHistoryStringFieldMixin);
    }
};

/**
 * History FK guiField class.
 * FK field for views for OneHistory model.
 */
guiFields.one_history_fk = class OneHistoryFkField extends spa.fields.fk.fk.FKField {
    static get mixins() {
        return super.mixins.concat(OneHistoryStringFieldMixin, OneHistoryFieldMixin);
    }
};

/**
 * History DATE_TIME guiField class.
 * DATE_TIME field for views for OneHistory model.
 */
guiFields.one_history_date_time = class OneHistoryDateTime extends spa.fields.datetime.DateTimeField {
    static get mixins() {
        return super.mixins.concat(OneHistoryStringFieldMixin);
    }

    /**
     * Redefinition of 'toRepresent' method of one_history_string guiField.
     */
    toRepresent(data = {}) {
        let value = data[this.options.name];

        if (!value) {
            return;
        }

        return moment(moment.tz(value, app.api.getTimeZone()))
            .tz(moment.tz.guess())
            .format('YYYY-MM-DD HH:mm:ss');
    }
};

/**
 * History UPTIME guiField class.
 * UPTIME field for views for OneHistory model.
 */
guiFields.one_history_uptime = class OneHistoryUpTime extends spa.fields.datetime.UptimeField {
    static get mixins() {
        return super.mixins.concat(OneHistoryStringFieldMixin);
    }
};

/**
 * History ONE_HISTORY_REVISION guiField class.
 * ONE_HISTORY_REVISION field for views for OneHistory model.
 */
guiFields.one_history_revision = class OneHistoryRevision extends guiFields.one_history_string {
    /**
     * Redefinition of 'toRepresent' method of one_history_string guiField.
     */
    toRepresent(data = {}) {
        let value = data[this.options.name];

        if (value) {
            return value.substr(0, 8);
        }
    }
};

/**
 * History ONE_HISTORY_CHOICES guiField class.
 * ONE_HISTORY_CHOICES field for views for OneHistory model.
 */
guiFields.one_history_choices = class OneHistoryChoices extends guiFields.choices {
    static get mixins() {
        return super.mixins.concat(OneHistoryStringFieldMixin, OneHistoryChoicesFieldMixin);
    }
};

/**
 * History ONE_HISTORY_RAW_INVENTORY guiField class.
 * ONE_HISTORY_RAW_INVENTORY field for views for OneHistory model.
 */
guiFields.one_history_raw_inventory = class OneHistoryRawInventoryField extends spa.fields.text
    .PlainTextField {
    static get mixins() {
        return super.mixins.concat(OneHistoryRawInventory);
    }
};

/**
 * History ONE_HISTORY_BOOLEAN guiField class.
 * ONE_HISTORY_BOOLEAN field for views for OneHistory model.
 */
guiFields.one_history_boolean = class OneHistoryBooleanField extends spa.fields.boolean.BooleanField {
    static get mixins() {
        return super.mixins.concat(OneHistoryStringFieldMixin, OneHistoryBooleanFieldMixin);
    }
};

/**
 * Field for array of modules names [{module: 'm1'}, {module: 'm2'}]
 */
guiFields.ansibleModulesList = class AnsibleModulesListField extends spa.fields.base.BaseField {
    toRepresent(data = {}) {
        let value = data[this.options.name];

        if (value) {
            return Object.values(value)
                .map((obj) => obj.module)
                .join(', ');
        }

        return '';
    }
};
