<?php

abstract class Field
{
    public static $type;

    public static function getDefinition(array $config)
    {
        return [
            'type' => static::$type,
            'name' => $config['name'],
            'label' => isset($config['label']) ? $config['label'] : $config['name'],
        ];
    }
}
