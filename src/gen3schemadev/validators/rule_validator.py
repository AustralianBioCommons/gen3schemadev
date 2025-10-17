# validates gen3 bundled jsonschema (.json) by testing gen3 specific business rules
import logging
from gen3schemadev.converter import link_suffix

logger = logging.getLogger(__name__)


class RuleValidator:
    def __init__(self, schema: dict):
        self.schema = schema

    def validate(self):
        self.data_file_link_core_metadata()
        self.link_props_exist()
        self.props_cannot_be_system_props()

    def _get_links(self):
        links = self.schema.get("links", [])
        logger.debug(f"Fetched links: {links}")
        if links and 'subgroup' in links[0]:
            logger.debug(
                f"Links contains 'subgroup', returning subgroup: {links[0]['subgroup']}"
            )
            return links[0]['subgroup']
        return links

    def _get_props(self):
        props = self.schema.get("properties", [])
        logger.debug(f"Fetched properties: {props}")
        return props

    def data_file_link_core_metadata(self):
        """
        If the schema has category: data_file,
        it must have a core metadata link.
        Raises informative exceptions when rule is violated.
        """
        try:
            category = self.schema.get("category")
            logger.debug(
                f"Checking if schema category is 'data_file'. Found: {category}"
            )
            schema_id = self.schema.get("id", "<unknown id>")
            if category == "data_file":
                links = self._get_links()
                logger.debug(f"Got links for data_file: {links}")
                for link in links:
                    if link.get("name") == link_suffix("core_metadata_collection"):
                        logger.debug(
                            f"Found core_metadata_collection link for data_file node (id: {schema_id})."
                        )
                        return True
                logger.warning(
                    f"No core_metadata_collection link found for data_file node (id: {schema_id})."
                )
                raise ValueError(
                    f"Schema '{schema_id}' with category 'data_file' must include a link with "
                    f"'name': 'core_metadata_collections'. Please add this link to the 'links' section."
                )
            return False
        except Exception as ex:
            schema_id = self.schema.get("id", "<unknown id>")
            raise RuntimeError(
                f"Exception occurred while validating core_metadata_collection link for schema '{schema_id}': {ex}"
            ) from ex

    def link_props_exist(self):
        """
        Ensures that properties exist for each link defined in the schema.

        Raises:
            ValueError: If a property corresponding to a link is missing, includes schema id
                        and offending link name for user troubleshooting.
            Exception: For unexpected errors.
        """
        try:
            links = self._get_links()
            link_name_list = []
            schema_id = self.schema.get("id", "<unknown id>")
            for link in links:
                link_name_list.append(link.get("name"))
            logger.debug(f"Collected link names for schema '{schema_id}': {link_name_list}")

            props = self._get_props()
            prop_keys = list(props.keys())
            logger.debug(f"Collected property keys for schema '{schema_id}': {prop_keys}")
            for link_name in link_name_list:
                if link_name not in prop_keys:
                    logger.error(
                        f"Property for link '{link_name}' does not exist in properties of schema '{schema_id}'."
                    )
                    raise ValueError(
                        f"In schema '{schema_id}', property for link '{link_name}' "
                        f"is missing from the 'properties' section. "
                        f"Please add a property named '{link_name}' to resolve this."
                    )
            logger.debug(
                f"All link names have corresponding properties for schema '{schema_id}'."
            )
            return True
        except Exception as ex:
            schema_id = self.schema.get("id", "<unknown id>")
            raise RuntimeError(
                f"Exception while verifying link properties for schema '{schema_id}': {ex}"
            ) from ex

    def _system_props(self):
        """returns a list of system properties 
        that you gen3 uses on the backend. You
        should not name any of your properties these.
        """
        system_props = [
            "id",
            "project_id",
            "type",
            "submitter_id",
            "state",
            "created_datetime",
            "updated_datetime",
            "file_state",
            "error_type",
        ]
        logger.debug(f"System properties: {system_props}")
        return system_props

    def props_cannot_be_system_props(self):
        props = self._get_props()
        prop_keys = list(props.keys())
        schema_id = self.schema.get("id", "<unknown id>")
        logger.debug(
            f"Checking user property keys against system properties for schema '{schema_id}': {prop_keys}"
        )
        try:
            for prop in prop_keys:
                if prop in self._system_props():
                    logger.error(
                        f"Property '{prop}' should not use a reserved system name in schema '{schema_id}'."
                    )
                    raise ValueError(
                        f"In schema '{schema_id}', property '{prop}' uses a reserved system property name. "
                        f"Please rename this property to avoid conflicts with internal Gen3 system fields."
                    )
            logger.debug(
                f"No property keys found that overlap with system properties in schema '{schema_id}'."
            )
            return True
        except Exception as ex:
            raise RuntimeError(
                f"Exception while checking for system property key conflicts in schema '{schema_id}': {ex}"
            ) from ex
