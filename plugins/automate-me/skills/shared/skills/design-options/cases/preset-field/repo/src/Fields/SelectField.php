<?php

class SelectField extends Field
{
    public static $type = 'select';

    public static function getDefinition(array $config)
    {
        $definition = parent::getDefinition($config);
        $definition['options'] = $config['options'];
        $definition['default'] = isset($config['default']) ? $config['default'] : null;
        return $definition;
    }
}
