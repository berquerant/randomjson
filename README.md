# randomjson

Generate random json.


# Example

example.json:

``` json
{
  "schema": {
    "items": [
      "{{repeat}}",
      "{{variable|n}}",
      {
        "user_id": [
          "{{function|uuid}}"
        ],
        "action": [
          "{{function|choice}}",
          "{{variable|actions}}"
        ],
        "url": [
          "{{function|format}}",
          "{{variable|url_template}}",
          [
            "{{function|rand}}",
            "{{const|100|int}}"
          ]
        ],
        "ref": [
          "{{cond}}",
          [
            [
              "{{function|eq}}",
              [
                "{{function|rand}}",
                "{{const|1|int}}"
              ],
              "{{const|1|int}}"
            ],
            [
              "{{function|format}}",
              "{{variable|ref_template}}",
              [
                "{{function|rand}}",
                "{{const|100|int}}"
              ]
            ]
          ]
        ]
      }
    ]
  },
  "variables": {
    "actions": [
      "pageview",
      "click",
      "conversion"
    ],
    "n": 3,
    "url_template": "https://sample{}.com",
    "ref_template": "https://sample{}.com/ref"
  }
}
```

`python -m randomjson.cli --input-json @example.json` generates below:

``` json
{
  "items": [
    {
      "user_id": "2d324eb1-0770-4444-bea8-d3de536da168",
      "action": [
        "conversion"
      ],
      "url": "https://sample3.com"
    },
    {
      "user_id": "526a4ca9-6b5a-483f-9869-8935c5524408",
      "action": [
        "pageview"
      ],
      "url": "https://sample16.com"
    },
    {
      "user_id": "7f2b8a89-cf75-4316-9152-07792b5830fc",
      "action": [
        "click"
      ],
      "url": "https://sample85.com",
      "ref": "https://sample49.com/ref"
    }
  ]
}
```
