<template>
  <div
    class="parser-channel-toolbar rounded-xl p-1.5 flex flex-col gap-2"
    role="group"
    :aria-label="ariaLabel"
  >
    <div class="parser-channel-toolbar__track flex flex-wrap sm:flex-nowrap gap-1.5">
      <button
        v-for="item in items"
        :key="item.key"
        type="button"
        class="parser-channel-toolbar__btn"
        :class="{
          'parser-channel-toolbar__btn--on': Boolean(modelValue[item.key]),
          'parser-channel-toolbar__btn--off': !modelValue[item.key],
          'parser-channel-toolbar__btn--readonly': !editable,
        }"
        :disabled="saving"
        :aria-disabled="!editable || saving"
        :title="item.hint"
        :aria-pressed="Boolean(modelValue[item.key])"
        @click="toggle(item.key)"
      >
        <span class="parser-channel-toolbar__vendor">{{ item.vendor }}</span>
        <span class="parser-channel-toolbar__label">{{ item.label }}</span>
        <span
          class="parser-channel-toolbar__dot"
          :class="modelValue[item.key] ? 'parser-channel-toolbar__dot--on' : 'parser-channel-toolbar__dot--off'"
          aria-hidden="true"
        />
      </button>
    </div>
    <p v-if="hint" class="parser-channel-toolbar__note text-[9px] m-0" style="color: var(--text-muted);">
      {{ hint }}
    </p>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
    validator: (v) =>
      v &&
      typeof v.physical_mail === 'boolean' &&
      typeof v.email === 'boolean' &&
      typeof v.enrichment === 'boolean',
  },
  editable: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  ariaLabel: { type: String, default: 'Каналы рассылки и обогащения' },
  hint: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const items = [
  {
    key: 'physical_mail',
    vendor: 'Lob',
    label: 'Физическая рассылка',
    hint: 'Физическая рассылка (Lob)',
  },
  {
    key: 'email',
    vendor: 'SendGrid',
    label: 'Электронная рассылка',
    hint: 'Электронная рассылка (SendGrid)',
  },
  {
    key: 'enrichment',
    vendor: 'BatchData',
    label: 'Обогащение контактов',
    hint: 'Обогащение контактов (BatchData)',
  },
]

function toggle(key) {
  if (!props.editable || props.saving) return
  emit('update:modelValue', {
    ...props.modelValue,
    [key]: !props.modelValue[key],
  })
}
</script>

<style scoped>
.parser-channel-toolbar {
  background: var(--bg-base);
  border: 1px solid var(--border);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.parser-channel-toolbar__track {
  width: 100%;
}

.parser-channel-toolbar__btn {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-secondary);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.15s,
    background 0.15s,
    color 0.15s,
    box-shadow 0.15s;
}

.parser-channel-toolbar__btn:hover:not(:disabled) {
  border-color: var(--border-active);
  color: var(--text-primary);
}

.parser-channel-toolbar__btn--readonly:not(.parser-channel-toolbar__btn--on):hover:not(:disabled) {
  border-color: var(--border);
  color: var(--text-secondary);
}

.parser-channel-toolbar__btn--on {
  border-color: rgba(74, 222, 128, 0.45);
  background: linear-gradient(165deg, rgba(74, 222, 128, 0.12) 0%, var(--bg-surface) 100%);
  color: var(--text-primary);
  box-shadow: 0 0 0 1px rgba(74, 222, 128, 0.08);
}

.parser-channel-toolbar__btn--off:not(.parser-channel-toolbar__btn--readonly) {
  opacity: 0.92;
}

.parser-channel-toolbar__btn--readonly {
  cursor: default;
}

.parser-channel-toolbar__btn:disabled {
  cursor: wait;
  opacity: 0.85;
}

.parser-channel-toolbar__btn[aria-disabled='true']:not(:disabled) {
  opacity: 1;
}

.parser-channel-toolbar__vendor {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.parser-channel-toolbar__btn--on .parser-channel-toolbar__vendor {
  color: var(--accent-green);
}

.parser-channel-toolbar__label {
  font-size: 11px;
  font-weight: 500;
  line-height: 1.25;
}

.parser-channel-toolbar__dot {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 7px;
  height: 7px;
  border-radius: 999px;
}

.parser-channel-toolbar__btn {
  position: relative;
  padding-right: 28px;
}

.parser-channel-toolbar__dot--on {
  background: var(--accent-green);
  box-shadow: 0 0 10px rgba(74, 222, 128, 0.5);
}

.parser-channel-toolbar__dot--off {
  background: var(--border-active);
}
</style>
