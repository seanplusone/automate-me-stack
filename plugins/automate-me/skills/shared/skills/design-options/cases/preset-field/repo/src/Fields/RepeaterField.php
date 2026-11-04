<?php

class RepeaterField extends Field
{
    public static $type = 'repeater';

    public static function getDefinition(array $config)
    {
        $definition = parent::getDefinition($config);
        $definition['children'] = $config['children'];
        return $definition;
    }
}
