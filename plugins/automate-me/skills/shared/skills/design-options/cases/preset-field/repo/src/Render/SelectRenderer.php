<?php

class SelectRenderer
{
    public function render(array $definition, $value)
    {
        $html = '<select name="' . e($definition['name']) . '">';
        foreach ($definition['options'] as $key => $label) {
            $selected = $key === $value ? ' selected' : '';
            $html .= '<option value="' . e($key) . '"' . $selected . '>' . e($label) . '</option>';
        }
        return $html . '</select>';
    }
}
