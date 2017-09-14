### Documents - Box integration.

All document types should be linked to `document category`.

`Order` value defines the order of specific document type in category.

`Short description` field is not used now.

`Description` field is used to represent hint of document type.

Field `Tags` is not used now.

If `Allow multiple documents` is checked - user will able to upload unlimited number of files for specific document type.

By setting `Per approval` and `Submission` fields, defines required or not should be document type for specific state of questionnaire. If allow multiple documents is `checked` and Per approval/Submission is Required, it means that **at least one** file should be uploaded.

Use `criteria` to hide or show document type depends on filled questionnaire data. This field will be removed in future. Developer should manage this logic on frontend side.

### Box Webhooks V1 SetUp

Official documentation: https://docs.box.com/docs/webhooks

#### List of required Event Triggers:

* Created
* Uploaded
* Deleted

#### Endpoint URL

Template: `*BASE_URL*/box/box-event-callback/`
Example of URL for beta server: `https://beta.sample.com/box/box-event-callback/`

#### List of required callback parameters
| Parameter name | Parameter value |
|---|---|
|item_id|#item_id#|
|event_type|#event_type#|
|from_user_id|#from_user_id#|
|item_parent_folder_id|#item_parent_folder_id#|
|token|<BOX_API_OAUTH_CLIENT_ID>|

#### Uploaded Box items

Uploaded from Box items will be duplicated on server side with default document type - 'Additional documents'. Default document type will be created if it doesn't exists.
